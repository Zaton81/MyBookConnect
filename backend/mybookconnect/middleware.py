import logging
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str: str):
    try:
        token = AccessToken(token_str)
        user_id = token.get("user_id")
        if not user_id:
            return AnonymousUser()
        user = User.objects.get(id=user_id)
        if not user.is_active:
            return AnonymousUser()
        # Verificar si la sesión fue revocada antes del timestamp de emisión del token
        from django.core.cache import cache
        token_iat = token.get("iat")
        if token_iat is not None:
            revocation_timestamp = cache.get(f"user_jwt_revoked_at_{user.id}")
            if revocation_timestamp is not None and float(token_iat) < float(revocation_timestamp):
                logger.info("Token de WebSocket rechazado por revocación de sesión para usuario %s", user.id)
                return AnonymousUser()
        return user
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        logger.debug("Error validando JWT en WebSocket: %s", e)
        return AnonymousUser()
    except Exception as e:
        logger.exception("Error inesperado al decodificar token en WebSocket: %s", e)
        return AnonymousUser()


@database_sync_to_async
def get_user_from_ticket(ticket_str: str):
    """Valida y consume un ticket efímero de uso único para conexión WebSocket."""
    from django.core.cache import cache

    key = f"ws_ticket_{ticket_str}"
    user_id = cache.get(key)
    if not user_id:
        logger.debug("Ticket de WebSocket inválido o expirado: %s", ticket_str)
        return AnonymousUser()

    # Consumir inmediatamente (single-use)
    cache.delete(key)

    try:
        user = User.objects.get(id=user_id)
        if not user.is_active:
            return AnonymousUser()
        return user
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    Middleware ASGI para Channels que autentica usuarios mediante ticket efímero
    (método recomendado / seguro), token JWT pasado en cookies seguras o headers,
    o query string (?token=...) como compatibilidad retroactiva.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token_str = None
        ticket_str = None
        headers = dict(scope.get("headers", []))
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)

        # 1. Prioridad: Ticket efímero de un solo uso (?ticket=...)
        if "ticket" in query_params:
            ticket_str = query_params["ticket"][0]
            scope["user"] = await get_user_from_ticket(ticket_str)
            return await self.app(scope, receive, send)

        # 2. Intentar obtener el token desde cookies (HttpOnly / Secure)
        if "cookies" in scope and isinstance(scope["cookies"], dict):
            token_str = (
                scope["cookies"].get("jwt_access_token")
                or scope["cookies"].get("access_token")
                or scope["cookies"].get("token")
            )

        if not token_str and b"cookie" in headers:
            try:
                cookie_header = headers[b"cookie"].decode("utf-8")
                cookie = SimpleCookie()
                cookie.load(cookie_header)
                for cookie_name in ("jwt_access_token", "access_token", "token"):
                    if cookie_name in cookie:
                        token_str = cookie[cookie_name].value
                        break
            except Exception as e:
                logger.debug("Error analizando cookies en WebSocket: %s", e)

        # 3. Headers (Authorization: Bearer ...)
        if not token_str and b"authorization" in headers:
            auth_header = headers[b"authorization"].decode("utf-8")
            if auth_header.startswith("Bearer "):
                token_str = auth_header[7:].strip()

        # 4. Fallback retroactivo: query string (?token=<token>)
        if not token_str and "token" in query_params:
            token_str = query_params["token"][0]

        # 5. Validar token y asignar usuario al scope
        if token_str:
            scope["user"] = await get_user_from_token(token_str)
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)


class ApiErrorContractMiddleware:
    """
    Middleware HTTP que garantiza que todas las respuestas de error (status >= 400)
    bajo rutas de la API (/api/) tengan la estructura unificada del contrato de errores,
    incluso si la vista devolvió directamente un Response(status=4xx) sin lanzar una excepción.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and response.status_code >= 400:
            try:
                from mybookconnect.exceptions import normalize_error_data

                if hasattr(response, "data") and isinstance(response.data, (dict, list)):
                    if not (isinstance(response.data, dict) and "error" in response.data):
                        response.data = normalize_error_data(
                            response.data,
                            response.status_code,
                            method=request.method,
                        )
                        if getattr(response, "_is_rendered", False):
                            response._is_rendered = False
                            response.render()
                elif "application/json" in response.get("Content-Type", ""):
                    import json

                    content = json.loads(response.content.decode("utf-8"))
                    if isinstance(content, (dict, list)):
                        if not (isinstance(content, dict) and "error" in content):
                            normalized = normalize_error_data(content, response.status_code, method=request.method)
                            response.content = json.dumps(normalized).encode("utf-8")
            except Exception as e:
                logger.debug("Error al normalizar contrato de error en middleware: %s", e)

        return response


class IdempotencyMiddleware:
    """
    Middleware HTTP para garantizar idempotencia automática cuando se proporcione
    la cabecera Idempotency-Key o X-Idempotency-Key en peticiones mutantes bajo /api/.
    Si la vista ya fue procesada por el decorador @idempotent, este middleware la omite.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/") or request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return self.get_response(request)

        # Si la vista ya se encargó de la idempotencia mediante decorador
        if getattr(request, "_idempotency_handled", False):
            return self.get_response(request)

        from django.http import JsonResponse

        from mybookconnect.idempotency import IdempotencyManager, IdempotencyStatus

        key = IdempotencyManager.extract_key(request)
        if not key:
            return self.get_response(request)

        user_id = getattr(request.user, "id", None) if getattr(request, "user", None) and request.user.is_authenticated else None
        cache_key = IdempotencyManager.build_cache_key(user_id, request.method, request.path, key)
        payload_hash = IdempotencyManager.compute_payload_hash(request)

        # 1. Comprobar registros existentes
        stored = IdempotencyManager.get_stored_record(cache_key)
        if stored:
            if stored.get("payload_hash") != payload_hash:
                err_data = {
                    "detail": "La clave de idempotencia ya fue utilizada con un cuerpo de petición diferente.",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "La clave de idempotencia ya fue utilizada con un cuerpo de petición diferente.",
                        "details": {"idempotency_key": "Payload mismatch for reused key"},
                    },
                }
                resp = JsonResponse(err_data, status=400)
                resp.data = err_data
                return resp

            if stored.get("status") == IdempotencyStatus.PROCESSING:
                err_data = {
                    "detail": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                        "details": {"idempotency_key": "Request in progress"},
                    },
                }
                resp = JsonResponse(err_data, status=409)
                resp.data = err_data
                return resp

            if stored.get("status") == IdempotencyStatus.COMPLETED:
                resp_data = stored.get("response_data")
                resp = JsonResponse(resp_data, status=stored.get("status_code", 200), safe=False)
                resp.data = resp_data
                resp["Idempotent-Replayed"] = "true"
                resp["Idempotency-Key"] = key
                return resp

        # 2. Adquirir bloqueo atómico
        if not IdempotencyManager.acquire_lock(cache_key):
            err_data = {
                "detail": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                    "details": {"idempotency_key": "Concurrent request lock active"},
                },
            }
            resp = JsonResponse(err_data, status=409)
            resp.data = err_data
            return resp

        IdempotencyManager.set_processing(cache_key, payload_hash)

        try:
            response = self.get_response(request)
            if getattr(request, "_idempotency_handled", False):
                return response

            if hasattr(response, "status_code") and response.status_code < 500:
                data_to_save = getattr(response, "data", None)
                if data_to_save is None and "application/json" in response.get("Content-Type", ""):
                    try:
                        import json

                        data_to_save = json.loads(response.content.decode("utf-8"))
                    except Exception:
                        pass

                if data_to_save is not None:
                    IdempotencyManager.save_response(
                        cache_key=cache_key,
                        payload_hash=payload_hash,
                        status_code=response.status_code,
                        response_data=data_to_save,
                    )

            if hasattr(response, "__setitem__"):
                response["Idempotency-Key"] = key

            return response
        finally:
            IdempotencyManager.release_lock(cache_key)


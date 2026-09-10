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
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        logger.debug("Error validando JWT en WebSocket: %s", e)
        return AnonymousUser()
    except Exception as e:
        logger.exception("Error inesperado al decodificar token en WebSocket: %s", e)
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    Middleware ASGI para Channels que autentica usuarios mediante token JWT
    pasado preferentemente en cookies seguras o headers de autorización,
    manteniendo query string (?token=...) como compatibilidad retroactiva.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token_str = None
        headers = dict(scope.get("headers", []))

        # 1. Intentar obtener el token desde cookies (HttpOnly / Secure)
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

        # 2. Si no viene en cookies, buscar en los headers (Authorization: Bearer ...)
        if not token_str and b"authorization" in headers:
            auth_header = headers[b"authorization"].decode("utf-8")
            if auth_header.startswith("Bearer "):
                token_str = auth_header[7:].strip()

        # 3. Fallback: query string (?token=<token>)
        if not token_str:
            query_string = scope.get("query_string", b"").decode("utf-8")
            query_params = parse_qs(query_string)
            if "token" in query_params:
                token_str = query_params["token"][0]

        # 4. Validar token y asignar usuario al scope
        if token_str:
            scope["user"] = await get_user_from_token(token_str)
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)

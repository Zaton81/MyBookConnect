import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

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
    pasado en la query string (?token=...) o en los headers (authorization: Bearer ...).
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token_str = None

        # 1. Intentar obtener el token desde la query string (?token=<token>)
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        if "token" in query_params:
            token_str = query_params["token"][0]

        # 2. Si no viene en query string, buscar en los headers
        if not token_str:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Bearer "):
                token_str = auth_header[7:].strip()

        # 3. Validar token y asignar usuario al scope
        if token_str:
            scope["user"] = await get_user_from_token(token_str)
        else:
            scope["user"] = AnonymousUser()

        return await self.app(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)

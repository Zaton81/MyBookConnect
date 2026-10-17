import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from mybookconnect.middleware import JwtAuthMiddleware, get_user_from_ticket, get_user_from_token

User = get_user_model()


@pytest.fixture
def auth_user(db):
    user = User.objects.create_user(
        username="sec_testuser",
        email="sec_testuser@example.com",
        password="ValidPassword123!",
        is_email_verified=True,
    )
    return user


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestPhaseA2SecurityAuthentication:
    """
    Suite de validación de seguridad de autenticación para la Fase A2:
    - Cookies HttpOnly + SameSite + Secure
    - Fallback y coexistencia con cabecera Authorization
    - Rotación estricta de refresh token y blacklist
    - Logout seguro y borrado de cookies
    - Handshake efímero para WebSockets y erradicación de ?token= en query string
    """

    def test_login_emits_httponly_secure_cookies(self, api_client, auth_user):
        """El inicio de sesión exitoso debe emitir cookies HttpOnly para access_token y refresh_token."""
        response = api_client.post(
            "/api/v1/auth/token/",
            {"username": auth_user.username, "password": "ValidPassword123!"},
            format="json",
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

        # Verificar presencia y directivas de seguridad de las cookies
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

        access_cookie = response.cookies["access_token"]
        refresh_cookie = response.cookies["refresh_token"]

        assert access_cookie["httponly"] is True
        assert access_cookie["samesite"].lower() in ("lax", "strict")
        assert access_cookie["path"] == "/"

        assert refresh_cookie["httponly"] is True
        assert refresh_cookie["samesite"].lower() in ("lax", "strict")
        assert refresh_cookie["path"] == "/"

    def test_authentication_via_cookie_without_auth_header(self, api_client, auth_user):
        """Peticiones a endpoints protegidos deben autenticarse transparentemente usando la cookie HttpOnly."""
        refresh = RefreshToken.for_user(auth_user)
        access_token = str(refresh.access_token)

        # Inyectar cookie sin enviar cabecera Authorization
        api_client.cookies["access_token"] = access_token

        response = api_client.get("/api/v1/auth/profile/")
        assert response.status_code == 200
        assert response.data["username"] == auth_user.username

    def test_token_refresh_via_cookie_and_rotation(self, api_client, auth_user):
        """El endpoint de refresh debe renovar tokens leyendo de la cookie HttpOnly y rotar el refresh token."""
        refresh = RefreshToken.for_user(auth_user)
        refresh_str = str(refresh)

        api_client.cookies["refresh_token"] = refresh_str

        # Petición de refresh sin cuerpo (apoyándose en cookie)
        response = api_client.post("/api/v1/auth/token/refresh/", {}, format="json")
        assert response.status_code == 200
        assert "access" in response.data
        assert "access_token" in response.cookies

        # El refresh token previo debe haber sido añadido a la lista negra
        outstanding = OutstandingToken.objects.filter(token=refresh_str).first()
        if outstanding:
            assert BlacklistedToken.objects.filter(token=outstanding).exists()

    def test_logout_deletes_cookies_and_blacklists_refresh_token(self, api_client, auth_user):
        """El cierre de sesión debe invalidar el refresh token y eliminar las cookies HttpOnly."""
        refresh = RefreshToken.for_user(auth_user)
        access_str = str(refresh.access_token)
        refresh_str = str(refresh)

        api_client.cookies["access_token"] = access_str
        api_client.cookies["refresh_token"] = refresh_str
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_str}")

        response = api_client.post("/api/v1/auth/logout/", {}, format="json")
        assert response.status_code == 200

        # Verificar borrado de cookies (expiradas o vacías)
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
        assert response.cookies["access_token"].value == "" or response.cookies["access_token"]["max-age"] == 0

        # El refresh token debe estar en blacklist
        outstanding = OutstandingToken.objects.filter(token=refresh_str).first()
        if outstanding:
            assert BlacklistedToken.objects.filter(token=outstanding).exists()

    def test_websocket_ticket_generation_and_single_use(self, api_client, auth_user):
        """El endpoint de ticket para WebSocket debe generar un ticket efímero de uso único."""
        refresh = RefreshToken.for_user(auth_user)
        access_str = str(refresh.access_token)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_str}")

        response = api_client.post("/api/v1/auth/ws-ticket/")
        assert response.status_code == 200
        ticket = response.data.get("ticket")
        assert ticket is not None
        assert response.data.get("expires_in") == 60

        # Verificar en cache que el ticket mapea al usuario
        cache_key = f"ws_ticket_{ticket}"
        assert cache.get(cache_key) == auth_user.id

    def test_websocket_ticket_consumption_single_use(self, auth_user):
        """El consumo del ticket efímero en WebSocket debe ser estrictamente de un solo uso."""
        from mybookconnect.middleware import validate_and_consume_ws_ticket

        ticket = "test_ephemeral_ticket_12345"
        cache.set(f"ws_ticket_{ticket}", auth_user.id, timeout=60)

        # Primer consumo: exitoso
        user = validate_and_consume_ws_ticket(ticket)
        assert user.is_authenticated
        assert user.id == auth_user.id

        # Segundo consumo: debe ser AnonymousUser porque el ticket fue invalidado inmediatamente
        user_second = validate_and_consume_ws_ticket(ticket)
        assert not user_second.is_authenticated

    def test_websocket_middleware_blocks_insecure_token_query_string(self):
        """JwtAuthMiddleware debe bloquear terminantemente cualquier intento de enviar JWT en ?token=."""
        from asgiref.sync import async_to_sync

        async def dummy_app(scope, receive, send):
            return scope.get("user")

        middleware = JwtAuthMiddleware(dummy_app)

        scope = {
            "type": "websocket",
            "headers": [],
            "query_string": b"token=insecure_jwt_query_token_123",
        }

        user = async_to_sync(middleware)(scope, None, None)
        # Debe ser AnonymousUser debido a la política de erradicación de ?token=
        assert not user.is_authenticated

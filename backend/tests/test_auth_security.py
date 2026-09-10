from django.contrib.auth import get_user_model
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from mybookconnect.middleware import JwtAuthMiddleware

User = get_user_model()


@pytest.mark.django_db
class TestAuthSecurityAndBlacklist:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='auth_secure_user',
            email='secure@test.com',
            password='Password123!',
        )

    def test_access_token_lifetime_15_minutes(self):
        """Verifica que el Access Token tenga una expiración estricta de 15 minutos (900s)."""
        refresh = RefreshToken.for_user(self.user)
        access_token_str = str(refresh.access_token)

        token = AccessToken(access_token_str)
        # La diferencia entre exp y iat debe ser exactamente 15 minutos (900 segundos)
        lifetime = token['exp'] - token['iat']
        assert lifetime == 900

    def test_token_rotation_and_blacklisting(self):
        """Verifica que rotar el refresh token revoque e invalide el token anterior en la blacklist."""
        res_login = self.client.post('/api/v1/auth/token/', {
            'username': 'auth_secure_user',
            'password': 'Password123!',
        })
        assert res_login.status_code == status.HTTP_200_OK
        initial_tokens = res_login.json()
        initial_refresh = initial_tokens['refresh']

        # 1. Refrescar token: debe devolver un nuevo access y un nuevo refresh
        res_refresh = self.client.post('/api/v1/auth/token/refresh/', {
            'refresh': initial_refresh,
        })
        assert res_refresh.status_code == status.HTTP_200_OK
        refreshed_tokens = res_refresh.json()
        assert 'access' in refreshed_tokens
        assert 'refresh' in refreshed_tokens
        rotated_refresh = refreshed_tokens['refresh']
        assert rotated_refresh != initial_refresh

        # 2. Reutilizar el refresh token anterior: debe fallar con 401 por estar en blacklist
        res_reuse = self.client.post('/api/v1/auth/token/refresh/', {
            'refresh': initial_refresh,
        })
        assert res_reuse.status_code == status.HTTP_401_UNAUTHORIZED

        # 3. El nuevo refresh token debe ser válido
        res_valid = self.client.post('/api/v1/auth/token/refresh/', {
            'refresh': rotated_refresh,
        })
        assert res_valid.status_code == status.HTTP_200_OK

    def test_logout_blacklists_refresh_token(self):
        """Verifica que el endpoint /api/v1/auth/logout/ añade el refresh token a la lista negra."""
        refresh = RefreshToken.for_user(self.user)
        refresh_str = str(refresh)
        access_str = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_str}')

        # Invocar logout
        res_logout = self.client.post('/api/v1/auth/logout/', {
            'refresh': refresh_str,
        })
        assert res_logout.status_code == status.HTTP_200_OK
        assert res_logout.json()['detail'] == 'Sesión cerrada exitosamente.'

        # El refresh token ya no puede usarse para obtener nuevos access tokens
        res_refresh = self.client.post('/api/v1/auth/token/refresh/', {
            'refresh': refresh_str,
        })
        assert res_refresh.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_validation(self):
        """Verifica validación de payload requerido en endpoint de logout."""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

        # Sin campo refresh
        res_empty = self.client.post('/api/v1/auth/logout/', {})
        assert res_empty.status_code == status.HTTP_400_BAD_REQUEST

        # Con token inválido
        res_invalid = self.client.post('/api/v1/auth/logout/', {'refresh': 'token_invalido_xyz'})
        assert res_invalid.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.asyncio
class TestWebSocketJwtMiddleware:
    async def dummy_app(self, scope, receive, send):
        return scope['user']

    async def test_auth_via_cookies(self):
        user = await User.objects.acreate(username='ws_cookie_user', email='wsc@test.com')
        token = str(AccessToken.for_user(user))

        middleware = JwtAuthMiddleware(self.dummy_app)
        scope = {
            'headers': [
                (b'cookie', f'jwt_access_token={token}; other_cookie=123'.encode('utf-8'))
            ]
        }
        res_user = await middleware(scope, None, None)
        assert res_user.is_authenticated
        assert res_user.id == user.id

    async def test_auth_via_authorization_header(self):
        user = await User.objects.acreate(username='ws_header_user', email='wsh@test.com')
        token = str(AccessToken.for_user(user))

        middleware = JwtAuthMiddleware(self.dummy_app)
        scope = {
            'headers': [
                (b'authorization', f'Bearer {token}'.encode('utf-8'))
            ]
        }
        res_user = await middleware(scope, None, None)
        assert res_user.is_authenticated
        assert res_user.id == user.id

    async def test_auth_via_query_string_fallback(self):
        user = await User.objects.acreate(username='ws_query_user', email='wsq@test.com')
        token = str(AccessToken.for_user(user))

        middleware = JwtAuthMiddleware(self.dummy_app)
        scope = {
            'headers': [],
            'query_string': f'token={token}'.encode('utf-8'),
        }
        res_user = await middleware(scope, None, None)
        assert res_user.is_authenticated
        assert res_user.id == user.id

    async def test_unauthenticated_when_token_invalid(self):
        middleware = JwtAuthMiddleware(self.dummy_app)
        scope = {
            'headers': [],
            'query_string': b'token=token_falso_invalido',
        }
        res_user = await middleware(scope, None, None)
        assert not res_user.is_authenticated

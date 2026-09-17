import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.tokens import email_verification_token_generator, encode_uid

User = get_user_model()


@pytest.mark.django_db
class TestPhase47PasswordSecurityAndAuth:
    def setup_method(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="securityuser",
            email="securityuser@example.com",
            password="StrongOldPass123!",
            first_name="Security",
            last_name="Tester",
        )

    def test_password_validator_rejects_weak_and_similar_passwords(self):
        """Valida que contraseñas cortas, numéricas o similares al usuario sean rechazadas."""
        # 1. Contraseña demasiado corta (< 8 caracteres)
        res_short = self.client.post('/api/v1/auth/register/', {
            'username': 'shortuser',
            'email': 'short@example.com',
            'password': '123',
            'password2': '123',
        })
        assert res_short.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in res_short.json()

        # 2. Contraseña completamente numérica
        res_numeric = self.client.post('/api/v1/auth/register/', {
            'username': 'numericuser',
            'email': 'numeric@example.com',
            'password': '12345678901234',
            'password2': '12345678901234',
        })
        assert res_numeric.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in res_numeric.json()

        # 3. Contraseña idéntica al nombre de usuario
        res_similar = self.client.post('/api/v1/auth/register/', {
            'username': 'myuniquename',
            'email': 'similar@example.com',
            'password': 'myuniquename',
            'password2': 'myuniquename',
        })
        assert res_similar.status_code == status.HTTP_400_BAD_REQUEST

    def test_authenticated_password_change_success(self):
        """Cambio de contraseña por usuario autenticado con validación de clave previa."""
        self.client.force_authenticate(user=self.user)

        # Intento con contraseña anterior errónea
        bad_res = self.client.post('/api/v1/auth/password/change/', {
            'old_password': 'WrongPassword999!',
            'new_password': 'NewSuperPass2026#',
            'new_password2': 'NewSuperPass2026#',
        })
        assert bad_res.status_code == status.HTTP_400_BAD_REQUEST
        assert 'old_password' in bad_res.json()

        # Cambio correcto
        good_res = self.client.post('/api/v1/auth/password/change/', {
            'old_password': 'StrongOldPass123!',
            'new_password': 'NewSuperPass2026#',
            'new_password2': 'NewSuperPass2026#',
        })
        assert good_res.status_code == status.HTTP_200_OK
        data = good_res.json()
        assert 'access' in data
        assert 'refresh' in data

        # Verificar que la nueva clave funciona en el modelo
        self.user.refresh_from_db()
        assert self.user.check_password('NewSuperPass2026#')

    def test_password_change_revokes_previous_sessions(self):
        """El cambio de contraseña debe revocar las sesiones y refresh tokens anteriores."""
        old_refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(user=self.user)

        self.client.post('/api/v1/auth/password/change/', {
            'old_password': 'StrongOldPass123!',
            'new_password': 'BrandNewPass2026#',
            'new_password2': 'BrandNewPass2026#',
            'revoke_other_sessions': True,
        })

        # El refresh token anterior debe quedar en la lista negra
        unauth_client = APIClient()
        refresh_res = unauth_client.post('/api/v1/auth/token/refresh/', {
            'refresh': str(old_refresh),
        })
        assert refresh_res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_reset_anti_enumeration(self):
        """La solicitud de reset responde idéntico existan o no las direcciones de correo."""
        # Correo existente
        res_exist = self.client.post('/api/v1/auth/password/reset/', {
            'email': self.user.email,
        })
        assert res_exist.status_code == status.HTTP_200_OK

        # Correo inexistente
        res_unknown = self.client.post('/api/v1/auth/password/reset/', {
            'email': 'nobody_ever_registered_12345@example.com',
        })
        assert res_unknown.status_code == status.HTTP_200_OK
        assert res_exist.json()['detail'] == res_unknown.json()['detail']

    def test_password_reset_confirm_flow(self):
        """Flujo completo de confirmación de restablecimiento con token efímero."""
        token = default_token_generator.make_token(self.user)
        uid = encode_uid(self.user.pk)

        # Intento con token corrupto
        bad_res = self.client.post('/api/v1/auth/password/reset/confirm/', {
            'uid': uid,
            'token': 'invalid-token-123',
            'new_password': 'ResetPass2026#',
            'new_password2': 'ResetPass2026#',
        })
        assert bad_res.status_code == status.HTTP_400_BAD_REQUEST

        # Confirmación exitosa
        good_res = self.client.post('/api/v1/auth/password/reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': 'ResetPass2026#',
            'new_password2': 'ResetPass2026#',
        })
        assert good_res.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.check_password('ResetPass2026#')

        # El token no puede reutilizarse
        reuse_res = self.client.post('/api/v1/auth/password/reset/confirm/', {
            'uid': uid,
            'token': token,
            'new_password': 'AnotherPass2026#',
            'new_password2': 'AnotherPass2026#',
        })
        assert reuse_res.status_code == status.HTTP_400_BAD_REQUEST

    def test_email_verification_flow(self):
        """Verificación de correo con token efímero y mutación de estado."""
        assert not self.user.is_email_verified

        self.client.force_authenticate(user=self.user)
        req_res = self.client.post('/api/v1/auth/email/verify-request/')
        assert req_res.status_code == status.HTTP_200_OK

        token = email_verification_token_generator.make_token(self.user)
        uid = encode_uid(self.user.pk)

        unauth = APIClient()
        confirm_res = unauth.post('/api/v1/auth/email/verify/', {
            'uid': uid,
            'token': token,
        })
        assert confirm_res.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        assert self.user.is_email_verified is True

        # El token no puede reutilizarse (hash cambia con is_email_verified=True)
        reuse_res = unauth.post('/api/v1/auth/email/verify/', {
            'uid': uid,
            'token': token,
        })
        assert reuse_res.status_code == status.HTTP_400_BAD_REQUEST

    def test_revoke_all_sessions_endpoint(self):
        """El endpoint revoke-all revoca todas las sesiones abiertas del usuario."""
        refresh1 = RefreshToken.for_user(self.user)
        refresh2 = RefreshToken.for_user(self.user)

        self.client.force_authenticate(user=self.user)
        revoke_res = self.client.post('/api/v1/auth/sessions/revoke-all/')
        assert revoke_res.status_code == status.HTTP_200_OK
        assert revoke_res.json()['revoked_count'] >= 2

        unauth = APIClient()
        r1 = unauth.post('/api/v1/auth/token/refresh/', {'refresh': str(refresh1)})
        r2 = unauth.post('/api/v1/auth/token/refresh/', {'refresh': str(refresh2)})
        assert r1.status_code == status.HTTP_401_UNAUTHORIZED
        assert r2.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_blacklists_refresh_token(self):
        """El endpoint de logout añade el refresh token provisto a la blacklist."""
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(user=self.user)

        logout_res = self.client.post('/api/v1/auth/logout/', {'refresh': str(refresh)})
        assert logout_res.status_code == status.HTTP_200_OK

        unauth = APIClient()
        refresh_res = unauth.post('/api/v1/auth/token/refresh/', {'refresh': str(refresh)})
        assert refresh_res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token_rotation_and_reuse_detection(self):
        """Rotación estricta de refresh token e invalidación inmediata del anterior."""
        refresh1 = RefreshToken.for_user(self.user)

        unauth = APIClient()
        rotate_res = unauth.post('/api/v1/auth/token/refresh/', {'refresh': str(refresh1)})
        assert rotate_res.status_code == status.HTTP_200_OK
        data = rotate_res.json()
        assert 'access' in data
        assert 'refresh' in data
        refresh2 = data['refresh']
        assert refresh2 != str(refresh1)

        # Intentar reutilizar refresh1 debe ser rechazado
        reuse_res = unauth.post('/api/v1/auth/token/refresh/', {'refresh': str(refresh1)})
        assert reuse_res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_google_oauth_login_provision_and_auth(self):
        """Inicio de sesión social con Google OAuth y provisión automática de usuario."""
        # 1. Nuevo usuario a través de Google
        res_new = self.client.post('/api/v1/auth/google/', {
            'id_token': 'test-google-token-googlenew@example.com',
        })
        assert res_new.status_code == status.HTTP_200_OK
        data = res_new.json()
        assert 'access' in data
        assert 'refresh' in data
        assert data['user']['email'] == 'googlenew@example.com'
        assert data['user']['is_email_verified'] is True

        created_user = User.objects.get(email='googlenew@example.com')
        assert not created_user.has_usable_password()

        # 2. Re-login de usuario existente con Google
        res_existing = self.client.post('/api/v1/auth/google/', {
            'id_token': 'test-google-token-googlenew@example.com',
        })
        assert res_existing.status_code == status.HTTP_200_OK
        assert res_existing.json()['user']['id'] == created_user.id

        # 3. Token inválido rechazado
        res_bad = self.client.post('/api/v1/auth/google/', {
            'id_token': 'unrecognized-bogus-token-xyz',
        })
        assert res_bad.status_code == status.HTTP_400_BAD_REQUEST

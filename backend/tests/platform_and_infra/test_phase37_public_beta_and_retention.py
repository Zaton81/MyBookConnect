"""
Suite de pruebas de integración para la Fase 37:
Apertura de Beta Pública, Feature Flags de Registro, Sistema Viral de Referidos
y Monitorización de Retención de Cohortes D1/D7/D30.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from beta.models import BetaInvitation
from beta.referral_service import ReferralService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def normal_user(db):
    return User.objects.create_user(
        username='reader37',
        email='reader37@example.com',
        password='StrongPassword123!',
        first_name='Reader',
        last_name='ThirtySeven',
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin37',
        email='admin37@example.com',
        password='AdminPassword123!',
    )


@pytest.mark.django_db
class TestPublicBetaRegistrationFlags:
    """Verificación de flags dinámicas de registro público y beta cerrada."""

    def test_registration_status_public_mode(self, api_client):
        """GET /api/v1/beta/registration-status/ debe ser público y reflejar modo 'public'."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            res = api_client.get('/api/v1/beta/registration-status/')
            assert res.status_code == status.HTTP_200_OK
            assert res.data['public_registration_enabled'] is True
            assert res.data['require_invitation'] is False
            assert res.data['mode'] == 'public'

    def test_registration_status_closed_beta_mode(self, api_client):
        """El endpoint debe reflejar modo 'closed_beta' si se requiere invitación."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=True):
            res = api_client.get('/api/v1/beta/registration-status/')
            assert res.status_code == status.HTTP_200_OK
            assert res.data['require_invitation'] is True
            assert res.data['mode'] == 'closed_beta'

    def test_registration_status_maintenance_mode(self, api_client):
        """El endpoint debe reflejar modo 'maintenance' si todo el registro está deshabilitado."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=False, REQUIRE_BETA_INVITATION=False):
            res = api_client.get('/api/v1/beta/registration-status/')
            assert res.status_code == status.HTTP_200_OK
            assert res.data['public_registration_enabled'] is False
            assert res.data['require_invitation'] is False
            assert res.data['mode'] == 'maintenance'

    def test_public_registration_without_code_succeeds(self, api_client):
        """En modo público por defecto, los usuarios pueden registrarse libremente sin código."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            payload = {
                'username': 'newpublicuser',
                'email': 'newpublicuser@example.com',
                'password': 'SecurePassword123!',
                'password2': 'SecurePassword123!',
                'first_name': 'New',
                'last_name': 'User',
            }
            res = api_client.post('/api/v1/users/register/', payload, format='json')
            assert res.status_code == status.HTTP_201_CREATED
            assert User.objects.filter(username='newpublicuser').exists()

    def test_closed_beta_requires_invitation_code(self, api_client):
        """Si REQUIRE_BETA_INVITATION=True, registrarse sin código devuelve 400."""
        with override_settings(REQUIRE_BETA_INVITATION=True):
            payload = {
                'username': 'blockeduser',
                'email': 'blockeduser@example.com',
                'password': 'SecurePassword123!',
                'password2': 'SecurePassword123!',
            }
            res = api_client.post('/api/v1/users/register/', payload, format='json')
            assert res.status_code == status.HTTP_400_BAD_REQUEST
            assert 'invitation_code' in res.data

    def test_closed_beta_rejects_invalid_invitation_code(self, api_client):
        """Si REQUIRE_BETA_INVITATION=True, registrarse con código falso devuelve 400."""
        with override_settings(REQUIRE_BETA_INVITATION=True):
            payload = {
                'username': 'fakecodeuser',
                'email': 'fakecodeuser@example.com',
                'password': 'SecurePassword123!',
                'password2': 'SecurePassword123!',
                'invitation_code': 'NON-EXISTENT-CODE-1234',
            }
            res = api_client.post('/api/v1/users/register/', payload, format='json')
            assert res.status_code == status.HTTP_400_BAD_REQUEST
            assert 'invitation_code' in res.data

    def test_closed_beta_accepts_valid_invitation_code_and_consumes_it(self, api_client):
        """Un código válido permite el registro y se descuenta su uso."""
        invitation = BetaInvitation.objects.create(
            code='BETA-ALLOWED-001',
            max_uses=1,
            uses_count=0,
            is_active=True,
        )

        with override_settings(REQUIRE_BETA_INVITATION=True):
            payload = {
                'username': 'accepteduser',
                'email': 'accepteduser@example.com',
                'password': 'SecurePassword123!',
                'password2': 'SecurePassword123!',
                'invitation_code': 'BETA-ALLOWED-001',
            }
            res = api_client.post('/api/v1/users/register/', payload, format='json')
            assert res.status_code == status.HTTP_201_CREATED

            invitation.refresh_from_db()
            assert invitation.uses_count == 1
            assert invitation.is_active is False  # Llegó a max_uses=1

    def test_maintenance_mode_rejects_all_registrations(self, api_client):
        """Si PUBLIC_REGISTRATION_ENABLED=False y REQUIRE_BETA_INVITATION=False, registro cerrado."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=False, REQUIRE_BETA_INVITATION=False):
            payload = {
                'username': 'maintuser',
                'email': 'maintuser@example.com',
                'password': 'SecurePassword123!',
                'password2': 'SecurePassword123!',
            }
            res = api_client.post('/api/v1/users/register/', payload, format='json')
            assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestViralReferralSystem:
    """Verificación del sistema de referidos entre lectores."""

    def test_referral_endpoints_require_authentication(self, api_client):
        """Los endpoints de referidos personales deben exigir IsAuthenticated."""
        res_code = api_client.get('/api/v1/beta/referrals/my-code/')
        assert res_code.status_code == status.HTTP_401_UNAUTHORIZED

        res_stats = api_client.get('/api/v1/beta/referrals/stats/')
        assert res_stats.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_can_get_or_create_referral_code(self, api_client, normal_user):
        """Un usuario autenticado puede solicitar su código de referido personal."""
        api_client.force_authenticate(user=normal_user)
        res = api_client.get('/api/v1/beta/referrals/my-code/')
        assert res.status_code == status.HTTP_200_OK
        assert 'code' in res.data
        assert res.data['code'].startswith('REF-')
        assert len(res.data['code']) <= 32
        assert res.data['max_uses'] > 0
        assert res.data['uses_count'] == 0
        assert res.data['remaining_uses'] == res.data['max_uses']

        # Idempotencia: Una segunda petición debe retornar el mismo código
        res_second = api_client.get('/api/v1/beta/referrals/my-code/')
        assert res_second.status_code == status.HTTP_200_OK
        assert res_second.data['code'] == res.data['code']

    def test_referral_stats_reflects_invited_friends(self, api_client, normal_user):
        """Las estadísticas reflejan exactamente el número de registros realizados con el código."""
        invitation = ReferralService.get_or_create_referral_code(normal_user)
        code = invitation.code

        # Un amigo se registra usando el código
        friend_client = APIClient()
        payload = {
            'username': 'referredfriend',
            'email': 'friend@example.com',
            'password': 'SecurePassword123!',
            'password2': 'SecurePassword123!',
            'invitation_code': code,
        }
        reg_res = friend_client.post('/api/v1/users/register/', payload, format='json')
        assert reg_res.status_code == status.HTTP_201_CREATED

        # Comprobar las estadísticas del usuario que refirió
        api_client.force_authenticate(user=normal_user)
        stats_res = api_client.get('/api/v1/beta/referrals/stats/')
        assert stats_res.status_code == status.HTTP_200_OK
        assert stats_res.data['code'] == code
        assert stats_res.data['uses_count'] == 1
        assert stats_res.data['remaining_uses'] == stats_res.data['max_uses'] - 1


@pytest.mark.django_db
class TestCohortRetentionInBetaMetrics:
    """Verificación de retención de cohortes D1/D7/D30 en el dashboard de beta."""

    def test_beta_metrics_endpoint_includes_retention_data(self, api_client, admin_user):
        """El endpoint administrativo /api/v1/beta/admin/metrics/ incluye la clave 'retention'."""
        api_client.force_authenticate(user=admin_user)
        res = api_client.get('/api/v1/beta/admin/metrics/')
        assert res.status_code == status.HTTP_200_OK
        assert 'retention' in res.data

        retention = res.data['retention']
        assert 'timeframe_days' in retention
        assert 'total_signups' in retention
        assert 'd1_retention_rate' in retention
        assert 'd7_retention_rate' in retention
        assert 'd30_retention_rate' in retention

    def test_beta_metrics_forbidden_for_regular_users(self, api_client, normal_user):
        """Los lectores normales no pueden acceder a las métricas del dashboard."""
        api_client.force_authenticate(user=normal_user)
        res = api_client.get('/api/v1/beta/admin/metrics/')
        assert res.status_code == status.HTTP_403_FORBIDDEN

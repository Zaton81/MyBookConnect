"""
Suite de pruebas de integración para la Fase 38:
Cierre de Beta, Auditoría Final y Release 1.0.0 General Availability (GA).
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from mybookconnect.version import get_version, get_version_info

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def ga_user(db):
    return User.objects.create_user(
        username='ga_user_100',
        email='ga_user@mybookconnect.local',
        password='StrongGaPassword123!',
        first_name='General',
        last_name='Availability',
    )


@pytest.mark.django_db
class TestGeneralAvailabilityVersion:
    """Verificación de corte de versión 1.0.0 definitiva sin sufijos pre-release."""

    def test_version_helpers(self):
        """Los helpers internos deben retornar 1.0.0 y metadatos limpios."""
        ver = get_version()
        assert ver == '1.0.0'

        info = get_version_info()
        assert info['version'] == '1.0.0'
        assert info['major'] == 1
        assert info['minor'] == 0
        assert info['patch'] == 0
        assert not info['prerelease']  # Cadena vacía o None
        assert info['semver'] is True

    def test_version_api_endpoint(self, api_client):
        """GET /api/v1/version/ debe responder versión 1.0.0 exacta."""
        res = api_client.get('/api/v1/version/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['version'] == '1.0.0'
        assert res.data['major'] == 1
        assert res.data['minor'] == 0
        assert res.data['patch'] == 0
        assert not res.data['prerelease']


@pytest.mark.django_db
class TestProductionHealthProbes:
    """Verificación de sondas de liveness y readiness para balanceadores de carga."""

    def test_liveness_probe(self, api_client):
        """GET /health/live debe responder 200 OK con estado saludable."""
        res = api_client.get('/health/live')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['status'] in ('healthy', 'live')

    def test_readiness_probe(self, api_client):
        """GET /health/ready debe verificar base de datos y caché."""
        res = api_client.get('/health/ready')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['status'] == 'ready'
        assert 'services' in res.data
        assert res.data['services']['database'] == 'ready'
        assert res.data['services']['cache'] == 'ready'


@pytest.mark.django_db
class TestGeneralAvailabilityUserLifecycle:
    """Verificación de ciclo de vida completo de usuario en modo de producción GA."""

    def test_public_registration_mode_by_default(self, api_client):
        """En modo GA, el endpoint de estado de registro debe reportar 'public'."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            res = api_client.get('/api/v1/beta/registration-status/')
            assert res.status_code == status.HTTP_200_OK
            assert res.data['mode'] == 'public'
            assert res.data['public_registration_enabled'] is True
            assert res.data['require_invitation'] is False

    def test_end_to_end_registration_and_login(self, api_client):
        """Un usuario puede registrarse libremente y obtener tokens JWT de sesión."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            reg_payload = {
                'username': 'ga_reader_2026',
                'email': 'ga_reader@example.com',
                'password': 'ComplexPassword2026!',
                'password2': 'ComplexPassword2026!',
                'first_name': 'Production',
                'last_name': 'Reader',
            }
            reg_res = api_client.post('/api/v1/users/register/', reg_payload, format='json')
            assert reg_res.status_code == status.HTTP_201_CREATED

            # Inicio de sesión inmediato mediante el endpoint canónico de JWT
            login_payload = {
                'username': 'ga_reader_2026',
                'password': 'ComplexPassword2026!',
            }
            login_res = api_client.post('/api/v1/auth/token/', login_payload, format='json')
            assert login_res.status_code == status.HTTP_200_OK
            assert 'access' in login_res.data
            assert 'refresh' in login_res.data


@pytest.mark.django_db
class TestProductionIntegrityAndLegalCompliance:
    """Verificación de cumplimiento legal RGPD y neutralidad en producción."""

    def test_legal_documents_accessible_publicly(self, api_client):
        """Las políticas legales y de privacidad deben estar expuestas públicamente."""
        res = api_client.get('/api/v1/books/legal/')
        assert res.status_code == status.HTTP_200_OK

    def test_referral_system_ready_for_production(self, api_client, ga_user):
        """El sistema de referidos virales funciona con el usuario en producción."""
        api_client.force_authenticate(user=ga_user)
        res = api_client.get('/api/v1/beta/referrals/my-code/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['code'].startswith('REF-')
        assert res.data['is_active'] is True

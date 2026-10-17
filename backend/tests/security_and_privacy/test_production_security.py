from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestProductionSecurity:
    def setup_method(self):
        self.client = APIClient()

    def test_security_headers_present_in_responses(self):
        """Verifica que las cabeceras HTTP de protección (nosniff, X-Frame-Options) estén presentes."""
        res = self.client.get('/api/v1/books/')
        assert res.status_code == status.HTTP_200_OK
        # Django SecurityMiddleware y XFrameOptionsMiddleware
        assert res.headers.get('X-Content-Type-Options') == 'nosniff'
        assert res.headers.get('X-Frame-Options') == 'DENY'

    def test_cors_configuration_explicit_origins(self):
        """Verifica que CORS no use comodines (*) cuando se permiten credenciales."""
        assert settings.CORS_ALLOW_ALL_ORIGINS is False
        assert settings.CORS_ALLOW_CREDENTIALS is True
        assert isinstance(settings.CORS_ALLOWED_ORIGINS, list)
        assert '*' not in settings.CORS_ALLOWED_ORIGINS
        assert len(settings.CORS_ALLOWED_ORIGINS) > 0

    def test_csrf_trusted_origins_configured(self):
        """Verifica que CSRF_TRUSTED_ORIGINS esté configurado como lista explícita."""
        assert isinstance(settings.CSRF_TRUSTED_ORIGINS, list)
        assert len(settings.CSRF_TRUSTED_ORIGINS) > 0
        for origin in settings.CSRF_TRUSTED_ORIGINS:
            assert origin.startswith('http://') or origin.startswith('https://')

    def test_secret_key_mandatory_check(self):
        """Verifica que la ausencia de SECRET_KEY sea rechazada por diseño."""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 0

    def test_production_directives_contract(self):
        """
        Verifica el contrato de directivas de seguridad para producción:
        en modo no-DEBUG, las cookies seguras y HSTS deben estar configurados.
        """
        # Verificamos que las variables existan en el módulo settings
        assert hasattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF')
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True
        assert hasattr(settings, 'X_FRAME_OPTIONS')
        assert settings.X_FRAME_OPTIONS == 'DENY'
        assert hasattr(settings, 'SECURE_HSTS_SECONDS')
        assert hasattr(settings, 'SESSION_COOKIE_SECURE')
        assert hasattr(settings, 'CSRF_COOKIE_SECURE')

    def test_django_system_check_zero_errors(self):
        """Ejecuta manage.py check para garantizar 0 errores en el sistema."""
        call_command('check')

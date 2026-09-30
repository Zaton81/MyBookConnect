import json
from pathlib import Path
import pytest
from django.conf import settings
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient
from mybookconnect.version import get_version, get_version_info


@pytest.mark.django_db
class TestPhase34ReleaseCandidate:
    """
    Suite de verificación y auditoría del Release Candidate (RC1) — MyBookConnect.
    Valida:
    - Versionado formal SemVer 2.0.0 (1.0.0-rc1) en endpoints y metadatos
    - Sondas de Liveness y Readiness (/health/live, /health/ready, /api/v1/health/)
    - Ausencia de migraciones pendientes de generar en toda la base de código
    - Validación formal del esquema OpenAPI 3.0 con drf-spectacular
    - Integridad de la plantilla de variables de entorno de producción (.env.production.example)
    - Sincronización entre backend, frontend y CHANGELOG.md
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()

    def test_version_endpoint_returns_semver_rc1(self):
        """Verifica que /api/v1/version/ retorne la versión SemVer 1.0.0-rc1 con metadatos completos."""
        response = self.client.get('/api/v1/version/')
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data['version'] == "1.0.0-rc1"
        assert data['major'] == 1
        assert data['minor'] == 0
        assert data['patch'] == 0
        assert data['prerelease'] == "rc1"
        assert data['api_version'] == "v1"
        assert data['semver'] is True

    def test_health_probes_reflect_rc1_version(self):
        """Verifica que las sondas de salud (liveness y readiness) reflejen el estado y versión 1.0.0-rc1."""
        # 1. Liveness check
        res_live = self.client.get('/health/live')
        assert res_live.status_code == status.HTTP_200_OK
        data_live = res_live.json()
        assert data_live['status'] == 'healthy'
        assert data_live['process'] == 'alive'
        assert data_live['version'] == '1.0.0-rc1'

        # 2. Readiness probe
        res_ready = self.client.get('/health/ready')
        assert res_ready.status_code == status.HTTP_200_OK
        data_ready = res_ready.json()
        assert data_ready['status'] == 'ready'
        assert data_ready['services']['database'] == 'ready'
        assert data_ready['services']['cache'] == 'ready'

        # 3. Healthcheck canónico de API
        res_api_health = self.client.get('/api/v1/health/')
        assert res_api_health.status_code == status.HTTP_200_OK
        assert res_api_health.json()['version'] == '1.0.0-rc1'

    def test_no_pending_database_migrations(self):
        """Verifica que no existan cambios en modelos de Django pendientes de generar migración."""
        # makemigrations con check=True y dry_run=True sale con error si hay cambios sin migrar
        try:
            call_command('makemigrations', check=True, dry_run=True)
        except SystemExit as exc:
            pytest.fail(f"Existen cambios en los modelos sin migración generada: código de salida {exc}")

    def test_openapi_schema_validation_passes(self):
        """Verifica que el esquema OpenAPI 3.0 generado por drf-spectacular pase la validación formal."""
        try:
            call_command('spectacular', validate=True)
        except Exception as exc:
            pytest.fail(f"La validación del esquema OpenAPI ha fallado: {exc}")

    def test_production_environment_template_completeness(self):
        """Verifica que .env.production.example contenga las variables críticas de producción."""
        possible_paths = [
            Path(__file__).resolve().parent.parent.parent / ".env.production.example",
            Path("/repo/.env.production.example"),
            Path("/app/.env.production.example"),
        ]
        env_prod_file = next((p for p in possible_paths if p.exists()), None)
        if env_prod_file is None:
            pytest.skip("Archivo .env.production.example no accesible en este entorno de prueba")

        content = env_prod_file.read_text(encoding="utf-8")
        critical_vars = [
            "SECRET_KEY",
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_HOST",
            "REDIS_HOST",
            "REDIS_PORT",
            "ALLOWED_HOSTS",
            "AMAZON_AFFILIATE_TAG",
            "SECURE_SSL_REDIRECT",
            "SESSION_COOKIE_SECURE",
            "CSRF_COOKIE_SECURE",
        ]

        for var in critical_vars:
            assert var in content, f"Variable requerida de producción ausente en .env.production.example: {var}"

    def test_changelog_and_package_version_consistency(self):
        """Verifica la coherencia entre CHANGELOG.md, package.json y version.py."""
        # 1. Frontend package.json
        pkg_paths = [
            Path(__file__).resolve().parent.parent.parent / "frontend" / "package.json",
            Path("/repo/frontend/package.json"),
        ]
        pkg_file = next((p for p in pkg_paths if p.exists()), None)
        if pkg_file:
            pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))
            assert pkg_data.get("version") == "1.0.0-rc1"

        # 2. CHANGELOG.md
        changelog_paths = [
            Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md",
            Path("/repo/CHANGELOG.md"),
        ]
        changelog_file = next((p for p in changelog_paths if p.exists()), None)
        if changelog_file:
            changelog_content = changelog_file.read_text(encoding="utf-8")
            assert "## [1.0.0-rc1]" in changelog_content, "No se encontró la sección [1.0.0-rc1] en CHANGELOG.md"

        # 3. version.py
        assert get_version() == "1.0.0-rc1"
        info = get_version_info()
        assert info["prerelease"] == "rc1"

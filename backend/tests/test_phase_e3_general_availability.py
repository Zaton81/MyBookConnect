"""
Suite de pruebas para la Fase E3 — General Availability (GA) endurecida (Roadmap Bloque E).

Verifica:
1. test_version_ga_semver_clean: Corte oficial de versión 1.0.0 sin sufijos pre-release en helpers y endpoint REST.
2. test_public_registration_ga_defaults: Configuración de registro público por defecto y alta de usuarios sin invitación.
3. test_production_health_and_metrics_probes: Sondas de salud públicas y protección estricta del panel de métricas operativas.
4. test_e2e_reader_journey_ga: Recorrido completo E2E de lector en GA (registro, JWT, perfil y estantería personal).
5. test_ga_documentation_and_on_call_artifacts_integrity: Integridad física y contractual de los artefactos de GA y manual de guardia.
"""

from pathlib import Path

import pytest
from django.conf import settings
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
def ga_users(db):
    regular = User.objects.create_user(
        username="ga_reader_standard",
        email="reader@example.com",
        password="ValidGaPassword2026!",
        first_name="Lector",
        last_name="Producción",
    )
    admin = User.objects.create_user(
        username="ga_ops_admin",
        email="ops@example.com",
        password="ValidGaPassword2026!",
        is_staff=True,
    )
    return {
        "regular": regular,
        "admin": admin,
    }


@pytest.mark.django_db
class TestGeneralAvailabilityHardened:
    """Conjunto de pruebas que certifican la preparación de producción en General Availability (GA)."""

    def test_version_ga_semver_clean(self, api_client):
        """
        Garantiza que la versión oficial del sistema es 1.0.0 (SemVer 2.0.0),
        sin etiquetas transitorias ni sufijos de pre-release.
        """
        # 1. Helper directo get_version
        version_str = get_version()
        assert version_str == "1.0.0"

        # 2. Diccionario de metadatos get_version_info
        info = get_version_info()
        assert info["version"] == "1.0.0"
        assert info["major"] == 1
        assert info["minor"] == 0
        assert info["patch"] == 0
        assert not info.get("prerelease")
        assert info.get("semver") is True

        # 3. Endpoint de API público
        res = api_client.get("/api/v1/version/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["version"] == "1.0.0"
        assert res.data["major"] == 1
        assert res.data["minor"] == 0
        assert res.data["patch"] == 0
        assert not res.data.get("prerelease")

    def test_public_registration_ga_defaults(self, api_client):
        """
        Verifica que en modo GA el estado de registro reporte modo público
        y permita el alta directa de nuevos lectores sin requerir código de cohorte.
        """
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            # 1. Comprobar endpoint de estado de registro
            status_res = api_client.get("/api/v1/beta/registration-status/")
            assert status_res.status_code == status.HTTP_200_OK
            assert status_res.data["mode"] == "public"
            assert status_res.data["public_registration_enabled"] is True
            assert status_res.data["require_invitation"] is False

            # 2. Registro libre sin inv_code
            payload = {
                "username": "new_ga_reader",
                "email": "new_ga_reader@example.com",
                "password": "StrongPassword2026!",
                "password2": "StrongPassword2026!",
                "first_name": "Nuevo",
                "last_name": "Lector",
            }
            reg_res = api_client.post("/api/v1/users/register/", payload, format="json")
            assert reg_res.status_code == status.HTTP_201_CREATED
            assert User.objects.filter(username="new_ga_reader").exists()

    def test_production_health_and_metrics_probes(self, api_client, ga_users):
        """
        Verifica que las sondas de liveness y readiness respondan correctamente
        y que el endpoint de telemetría y métricas operativas esté protegido contra accesos indebidos.
        """
        # 1. Sonda de Liveness
        live_res = api_client.get("/health/live")
        assert live_res.status_code == status.HTTP_200_OK
        assert live_res.data["status"] in ("healthy", "live")

        # 2. Sonda de Readiness
        ready_res = api_client.get("/health/ready")
        assert ready_res.status_code == status.HTTP_200_OK
        assert ready_res.data["status"] == "ready"
        assert ready_res.data["services"]["database"] == "ready"
        assert ready_res.data["services"]["cache"] == "ready"

        # 3. Métricas operativas anónimas -> 401
        metrics_anon = api_client.get("/api/v1/observability/metrics/")
        assert metrics_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # 4. Métricas operativas con usuario estándar -> 403 Forbidden
        api_client.force_authenticate(user=ga_users["regular"])
        metrics_forbidden = api_client.get("/api/v1/observability/metrics/")
        assert metrics_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # 5. Métricas operativas con personal autorizado (is_staff) -> 200 OK
        api_client.force_authenticate(user=ga_users["admin"])
        metrics_admin = api_client.get("/api/v1/observability/metrics/")
        assert metrics_admin.status_code == status.HTTP_200_OK
        assert "backend_metrics" in metrics_admin.data
        assert "product_metrics" in metrics_admin.data
        assert "system_alerts" in metrics_admin.data
        assert "timestamp" in metrics_admin.data

    def test_e2e_reader_journey_ga(self, api_client):
        """
        Simula el viaje completo de un lector en GA: registro directo, login para
        obtención de tokens JWT, lectura de perfil y consulta de estantería.
        """
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=False):
            # 1. Registro
            reg_data = {
                "username": "journey_reader",
                "email": "journey@example.com",
                "password": "SafePassword2026!",
                "password2": "SafePassword2026!",
            }
            reg_res = api_client.post("/api/v1/users/register/", reg_data, format="json")
            assert reg_res.status_code == status.HTTP_201_CREATED

            # 2. Obtención de token JWT
            token_res = api_client.post(
                "/api/v1/auth/token/",
                {"username": "journey_reader", "password": "SafePassword2026!"},
                format="json",
            )
            assert token_res.status_code == status.HTTP_200_OK
            access_token = token_res.data["access"]
            assert access_token is not None

            # 3. Consulta de perfil autenticado con Bearer
            api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
            profile_res = api_client.get("/api/v1/users/profile/")
            assert profile_res.status_code == status.HTTP_200_OK
            assert profile_res.data["username"] == "journey_reader"

            # 4. Consulta de estantería de libros personal
            books_res = api_client.get("/api/v1/books/user/books/")
            assert books_res.status_code == status.HTTP_200_OK
            # Biblioteca inicial vacía pero accesible
            assert isinstance(books_res.data.get("results", books_res.data), list)

    def test_ga_documentation_and_on_call_artifacts_integrity(self):
        """
        Verifica la presencia y consistencia contractual de los documentos
        de gobernanza, cierre de beta y manual de guardia on-call 24/7.
        """
        docs_dir = Path(settings.BASE_DIR) / "docs"

        # 1. Informe de cierre de beta
        beta_closure = docs_dir / "deployment" / "beta_closure_report.md"
        assert beta_closure.exists(), f"Falta {beta_closure}"
        closure_text = beta_closure.read_text(encoding="utf-8")
        assert "General Availability — GA" in closure_text
        assert "1.0.0" in closure_text
        assert "Definition of Done" in closure_text

        # 2. Anuncio oficial de release
        announcement = docs_dir / "deployment" / "ga_release_announcement.md"
        assert announcement.exists(), f"Falta {announcement}"
        announcement_text = announcement.read_text(encoding="utf-8")
        assert "1.0.0" in announcement_text
        assert "mybooksocial.com" in announcement_text
        assert "General Availability" in announcement_text

        # 3. Manual de guardia y respuesta a incidentes
        on_call = docs_dir / "devops" / "on_call_runbook.md"
        assert on_call.exists(), f"Falta {on_call}"
        on_call_text = on_call.read_text(encoding="utf-8")
        assert "SEV-1" in on_call_text
        assert "SEV-2" in on_call_text
        assert "SEV-3" in on_call_text
        assert "Primary On-Call" in on_call_text
        assert "Post-Mortem Blameless" in on_call_text

        # 4. Guía general de General Availability
        ga_guide = docs_dir / "deployment" / "general_availability_release_guide.md"
        assert ga_guide.exists(), f"Falta {ga_guide}"

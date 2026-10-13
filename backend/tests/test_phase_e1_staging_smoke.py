"""
Suite de pruebas para la Fase E1 — Staging y Smoke Tests (Roadmap v2.0 - Bloque E).

Valida:
1. Sondas de Liveness y Readiness (/health/live y /health/ready) con contratos seguros.
2. Flujo completo de autenticación segura (cookies HttpOnly/Secure) y ticket efímero WebSocket (un solo uso).
3. Control de feature flags de registro público e invitaciones (/api/v1/beta/registration-status/).
4. Comando de verificación de integridad post-restauración (verify_restore_integrity).
5. Coherencia e integridad de scripts y checklist de pre-despliegue de Staging.
"""

from io import StringIO
import json
from pathlib import Path
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Author, Book, Review
from mybookconnect.middleware import validate_and_consume_ws_ticket

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staging_env(db):
    """Genera datos base para pruebas de smoke testing en staging."""
    user = User.objects.create_user(
        username="staging_smoke_user",
        email="smoke@staging.mybooksocial.com",
        password="StagingPassword123!",
        is_email_verified=True,
    )

    author = Author.objects.create(name="Arthur C. Clarke")
    book = Book.objects.create(
        title="2001: Una odisea espacial",
        isbn="9788466332159",
        author=author,
        average_rating=4.7,
        page_count=250,
    )
    Review.objects.create(
        user=user,
        book=book,
        rating=5,
        title="Monolito",
        text="Misterioso y fascinante.",
    )

    return {
        "user": user,
        "author": author,
        "book": book,
    }


@pytest.mark.django_db
class TestStagingHealthAndReadiness:
    def test_liveness_probe_contract(self, api_client):
        """La sonda de liveness debe retornar 200 OK y metadatos saludables."""
        response = api_client.get("/health/live")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["process"] == "alive"
        assert "version" in data

    def test_readiness_probe_contract_and_sanitization(self, api_client):
        """La sonda de readiness debe reportar los servicios listos sin filtrar secretos."""
        response = api_client.get("/health/ready")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert "services" in data
        assert data["services"]["database"] == "ready"
        assert data["services"]["cache"] == "ready"

        # Asegurar que no hay credenciales ni trazas de contraseña en el payload
        raw_body = json.dumps(data).lower()
        assert "password" not in raw_body
        assert "secret" not in raw_body


@pytest.mark.django_db
class TestStagingAuthenticationAndWebSocketTicket:
    def test_auth_login_emits_httponly_cookies(self, api_client, staging_env):
        """El login seguro en staging emite cookies HttpOnly sin filtrar tokens en query string."""
        user = staging_env["user"]
        response = api_client.post(
            "/api/v1/auth/token/",
            {"username": user.username, "password": "StagingPassword123!"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

        access_cookie = response.cookies["access_token"]
        assert access_cookie["httponly"] is True
        assert access_cookie["samesite"].lower() in ("lax", "strict")

    def test_websocket_ephemeral_ticket_generation_and_single_use(self, api_client, staging_env):
        """El ticket efímero de WebSocket se emite autenticado y es estrictamente de un solo uso."""
        user = staging_env["user"]
        refresh = RefreshToken.for_user(user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")

        # 1. Generar ticket
        response = api_client.post("/api/v1/auth/ws-ticket/")
        assert response.status_code == status.HTTP_200_OK
        ticket = response.data.get("ticket")
        assert ticket is not None
        assert response.data.get("expires_in") == 60

        # 2. Primer consumo: exitoso
        consumed_user = validate_and_consume_ws_ticket(ticket)
        assert consumed_user.is_authenticated
        assert consumed_user.id == user.id

        # 3. Segundo consumo: rechazado inmediatamente (un solo uso)
        second_attempt = validate_and_consume_ws_ticket(ticket)
        assert not second_attempt.is_authenticated


@pytest.mark.django_db
class TestStagingRegistrationFeatureFlags:
    def test_registration_status_endpoint(self, api_client):
        """El endpoint público /api/v1/beta/registration-status/ expone las banderas de control."""
        response = api_client.get("/api/v1/beta/registration-status/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert "public_registration_enabled" in data
        assert "require_invitation" in data
        assert "mode" in data

    def test_registration_blocked_when_invitation_required(self, api_client):
        """Cuando se requiere invitación de beta, un registro sin código es rechazado con 400 Bad Request."""
        with override_settings(PUBLIC_REGISTRATION_ENABLED=True, REQUIRE_BETA_INVITATION=True):
            response = api_client.post(
                "/api/v1/users/register/",
                {
                    "username": "uninvited_candidate",
                    "email": "uninvited@example.com",
                    "password": "ValidPassword123!",
                    "password2": "ValidPassword123!",
                    "invitation_code": "",
                },
                format="json",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "invitation_code" in response.data


@pytest.mark.django_db
class TestStagingRestoreIntegrityCheck:
    def test_verify_restore_integrity_command_passes(self, staging_env):
        """El comando de verificación de integridad post-restore aprueba el estado de la base de datos."""
        out = StringIO()
        call_command("verify_restore_integrity", "--json", stdout=out)
        output_str = out.getvalue()

        report = json.loads(output_str)
        assert report["status"] == "PASS"
        assert len(report["errors"]) == 0
        assert "users" in report["subsystems"]
        assert "catalog" in report["subsystems"]
        assert "interactions" in report["subsystems"]
        assert report["subsystems"]["users"]["total_users"] >= 1
        assert report["subsystems"]["catalog"]["total_books"] >= 1
        assert report["subsystems"]["interactions"]["total_reviews"] >= 1


class TestStagingPreflightAndChecklistIntegrity:
    def test_preflight_and_smoke_scripts_exist(self):
        """Verifica la presencia física de los scripts de staging y del checklist pre-despliegue."""
        base_dir = Path(settings.BASE_DIR)
        root_dir = base_dir if (base_dir / "scripts").exists() else base_dir.parent

        smoke_script = root_dir / "scripts" / "staging" / "smoke_test_staging.py"
        preflight_script = root_dir / "scripts" / "staging" / "preflight_staging.sh"
        checklist_doc = root_dir / "docs" / "deployment" / "pre_deployment_security_checklist.md"

        assert smoke_script.exists()
        assert preflight_script.exists()
        assert checklist_doc.exists()

        content = checklist_doc.read_text(encoding="utf-8")
        assert "mybooksocial.com" in content
        assert "HSTS" in content
        assert "HttpOnly" in content

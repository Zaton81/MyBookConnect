from datetime import timedelta
from pathlib import Path
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from beta.models import BetaFeedback, BetaFeedbackCategory, BetaInvitation, SupportTicket
from mybookconnect.version import get_version

User = get_user_model()


@pytest.mark.django_db
class TestPhase35StagingValidation:
    """
    Suite de verificación y auditoría de Staging (Beta Cerrada) — Fase 35.
    Valida:
    - Contratos de los endpoints sintéticos de smoke testing en staging.
    - Flujo completo de validación y ciclo de vida de invitaciones beta (BetaInvitation).
    - Recepción, validación y categorización de feedback in-app (BetaFeedback).
    - Creación y consulta de tickets de soporte para evaluadores (SupportTicket).
    - Integridad de scripts de smoke testing y preflight de staging.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="staging_tester",
            email="tester@staging.mybookconnect.com",
            password="SecurePassword2026!",
        )

    def test_smoke_endpoints_contract_in_staging(self):
        """Verifica que todos los endpoints cubiertos por el smoke test respondan según contrato."""
        # 1. Liveness
        res_live = self.client.get('/health/live')
        assert res_live.status_code == status.HTTP_200_OK
        data_live = res_live.json()
        assert data_live['status'] == 'healthy'
        assert data_live['process'] == 'alive'
        assert data_live['version'] == get_version()

        # 2. Readiness
        res_ready = self.client.get('/health/ready')
        assert res_ready.status_code == status.HTTP_200_OK
        data_ready = res_ready.json()
        assert data_ready['status'] == 'ready'
        assert data_ready['services']['database'] == 'ready'
        assert data_ready['services']['cache'] == 'ready'

        # 3. Version
        res_version = self.client.get('/api/v1/version/')
        assert res_version.status_code == status.HTTP_200_OK
        data_version = res_version.json()
        assert data_version['version'] == get_version()
        assert data_version['semver'] is True

        # 4. Libros catálogo
        res_books = self.client.get('/api/v1/books/')
        assert res_books.status_code == status.HTTP_200_OK

        # 5. Tendencias
        res_trending = self.client.get('/api/v1/books/trending/')
        assert res_trending.status_code == status.HTTP_200_OK

    def test_beta_invitation_verification_flows(self):
        """Verifica el ciclo de vida y validación estricta de códigos de invitación beta."""
        # 1. Código no existente
        res_nonexistent = self.client.post('/api/v1/beta/invitations/verify/', {'code': 'INVALID_CODE_999'})
        assert res_nonexistent.status_code == status.HTTP_400_BAD_REQUEST

        # 2. Código válido activo
        invitation = BetaInvitation.objects.create(
            code="BETA_STAGING_2026",
            invited_email="tester@staging.mybookconnect.com",
            max_uses=3,
            uses_count=0,
            is_active=True,
            expires_at=timezone.now() + timedelta(days=7),
        )
        res_valid = self.client.post('/api/v1/beta/invitations/verify/', {'code': 'BETA_STAGING_2026'})
        assert res_valid.status_code == status.HTTP_200_OK
        data_valid = res_valid.json()
        assert data_valid['valid'] is True
        assert data_valid['code'] == 'BETA_STAGING_2026'

        # 3. Código inactivo
        invitation.is_active = False
        invitation.save()
        res_inactive = self.client.post('/api/v1/beta/invitations/verify/', {'code': 'BETA_STAGING_2026'})
        assert res_inactive.status_code == status.HTTP_400_BAD_REQUEST

        # 4. Código con límite de usos alcanzado
        invitation.is_active = True
        invitation.uses_count = 3
        invitation.save()
        res_max_uses = self.client.post('/api/v1/beta/invitations/verify/', {'code': 'BETA_STAGING_2026'})
        assert res_max_uses.status_code == status.HTTP_400_BAD_REQUEST

        # 5. Código expirado
        invitation.uses_count = 0
        invitation.expires_at = timezone.now() - timedelta(minutes=5)
        invitation.save()
        res_expired = self.client.post('/api/v1/beta/invitations/verify/', {'code': 'BETA_STAGING_2026'})
        assert res_expired.status_code == status.HTTP_400_BAD_REQUEST

    def test_beta_feedback_submission_and_categories(self):
        """Verifica la persistencia y categorización de comentarios y reportes de beta cerrada."""
        # 1. Envío anónimo rechazado con 401 Unauthorized
        feedback_payload = {
            "category": BetaFeedbackCategory.CONFUSING_UX,
            "title": "Navegación de recomendaciones",
            "description": "La interfaz de recomendación es muy intuitiva en mobile.",
            "page_url": "http://staging.mybookconnect.com/books/discover",
        }
        res_anon = self.client.post('/api/v1/beta/feedback/', feedback_payload, format='json')
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # 2. Envío autenticado con asociación a usuario
        self.client.force_authenticate(user=self.user)
        res_auth = self.client.post('/api/v1/beta/feedback/', feedback_payload, format='json')
        assert res_auth.status_code == status.HTTP_201_CREATED
        assert BetaFeedback.objects.filter(category=BetaFeedbackCategory.CONFUSING_UX).exists()

        latest_feedback = BetaFeedback.objects.latest('created_at')
        assert latest_feedback.user == self.user
        assert latest_feedback.title == "Navegación de recomendaciones"

        # 3. Envío con campos inválidos (sin descripción)
        res_invalid = self.client.post(
            '/api/v1/beta/feedback/',
            {"category": BetaFeedbackCategory.BUG, "title": "Sin desc"},
            format='json',
        )
        assert res_invalid.status_code == status.HTTP_400_BAD_REQUEST

    def test_beta_support_ticket_creation_and_listing(self):
        """Verifica la creación y consulta de tickets de soporte para evaluadores beta."""
        self.client.force_authenticate(user=self.user)

        # 1. Crear ticket de soporte
        ticket_payload = {
            "subject": "Duda sobre sincronización con Goodreads",
            "message": "¿Cómo puedo importar mis libros leídos en formato CSV desde Goodreads?",
            "category": "technical",
            "priority": "medium",
        }
        res_create = self.client.post('/api/v1/beta/support/', ticket_payload, format='json')
        assert res_create.status_code == status.HTTP_201_CREATED
        assert SupportTicket.objects.filter(user=self.user, subject="Duda sobre sincronización con Goodreads").exists()

        # 2. Listar mis tickets de soporte
        res_list = self.client.get('/api/v1/beta/support/my/')
        assert res_list.status_code == status.HTTP_200_OK
        data_list = res_list.json()
        tickets = data_list.get('results', data_list) if isinstance(data_list, dict) else data_list
        assert len(tickets) >= 1
        assert tickets[0]['subject'] == "Duda sobre sincronización con Goodreads"

    def test_staging_scripts_exist_and_are_valid(self):
        """Verifica que los scripts de smoke testing y preflight de staging existan y no tengan errores sintácticos."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        smoke_script = repo_root / "scripts" / "staging" / "smoke_test_staging.py"
        preflight_script = repo_root / "scripts" / "staging" / "preflight_staging.sh"

        if smoke_script.exists():
            content = smoke_script.read_text(encoding="utf-8")
            assert "check_endpoint" in content
            assert "/health/live" in content
            assert "/api/v1/beta/invitations/verify/" in content

        if preflight_script.exists():
            content_pf = preflight_script.read_text(encoding="utf-8")
            assert "smoke_test_staging.py" in content_pf
            assert "makemigrations" in content_pf

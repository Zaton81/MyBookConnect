import csv
import json
from pathlib import Path
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework import status
from rest_framework.test import APIClient

from beta.alerts_service import BetaAlertsService
from beta.metrics_service import BetaMetricsService
from beta.models import (
    BetaFeedback,
    BetaFeedbackCategory,
    BetaFeedbackStatus,
    BetaInvitation,
    SupportTicket,
    SupportTicketPriority,
    SupportTicketStatus,
)

User = get_user_model()


@pytest.mark.django_db
class TestPhase36BetaCohort:
    """
    Suite de pruebas para la Fase 36: Apertura de Cohorte Beta Cerrada y Monitorización.
    Valida:
    - Generación masiva y exportación de invitaciones por cohortes con comando CLI.
    - Servicio y endpoint de telemetría y métricas de activación de evaluadores.
    - Sistema de triaje y alertas inmediatas ante reportes de bugs o tickets críticos.
    - Restricciones de autorización (IsAdminUser) en endpoints administrativos.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.regular_user = User.objects.create_user(
            username="evaluator_user",
            email="evaluator@example.com",
            password="Password123!",
        )
        self.admin_user = User.objects.create_superuser(
            username="admin_cohort",
            email="admin@example.com",
            password="AdminPassword123!",
        )

    def test_generate_beta_cohort_command_nominal(self):
        """Verifica la generación de invitaciones por lotes con prefijo de cohorte y límites."""
        initial_count = BetaInvitation.objects.count()
        call_command('generate_beta_cohort', cohort='ALFA1', count=5, max_uses=2, days=20)

        assert BetaInvitation.objects.count() == initial_count + 5
        cohort_invs = BetaInvitation.objects.filter(code__startswith='ALFA1-')
        assert cohort_invs.count() == 5

        for inv in cohort_invs:
            assert len(inv.code) <= 32
            assert inv.max_uses == 2
            assert inv.uses_count == 0
            assert inv.is_active is True
            assert inv.is_valid() is True

    def test_generate_beta_cohort_command_json_and_csv_export(self, tmp_path):
        """Verifica la exportación en disco de los códigos generados en formato JSON y CSV."""
        json_file = tmp_path / "cohort_export.json"
        csv_file = tmp_path / "cohort_export.csv"

        call_command(
            'generate_beta_cohort',
            cohort='FOUNDERS',
            count=3,
            export_json=str(json_file),
            export_csv=str(csv_file),
        )

        assert json_file.exists()
        json_data = json.loads(json_file.read_text(encoding='utf-8'))
        assert len(json_data) == 3
        assert json_data[0]['cohort'] == 'FOUNDERS'
        assert json_data[0]['code'].startswith('FOUNDERS-')

        assert csv_file.exists()
        with csv_file.open('r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 3
            assert rows[0]['cohort'] == 'FOUNDERS'

    def test_generate_beta_cohort_validation_errors(self):
        """Verifica que el comando rechace parámetros numéricos inválidos."""
        with pytest.raises(CommandError, match="--count debe ser mayor que cero"):
            call_command('generate_beta_cohort', count=0)

        with pytest.raises(CommandError, match="--max-uses debe ser mayor que cero"):
            call_command('generate_beta_cohort', max_uses=0)

        with pytest.raises(CommandError, match="--days debe ser mayor que cero"):
            call_command('generate_beta_cohort', days=0)

    def test_beta_cohort_metrics_service_and_endpoint(self):
        """Verifica el cálculo de KPIs de cohorte y el endpoint administrativo protegido."""
        # Sembrar datos para la prueba
        BetaInvitation.objects.create(code="METRICS-1", max_uses=2, uses_count=1, is_active=True)
        BetaInvitation.objects.create(code="METRICS-2", max_uses=1, uses_count=0, is_active=True)

        BetaFeedback.objects.create(
            user=self.regular_user,
            category=BetaFeedbackCategory.BUG,
            title="Error en login",
            description="Fallo de autenticación",
            status=BetaFeedbackStatus.NEW,
        )
        SupportTicket.objects.create(
            user=self.regular_user,
            subject="Problema crítico",
            message="No puedo abrir mi biblioteca",
            priority=SupportTicketPriority.CRITICAL,
            status=SupportTicketStatus.OPEN,
        )

        # 1. Comprobación directa del servicio
        metrics = BetaMetricsService.get_cohort_summary_metrics()
        assert metrics['invitations']['total'] >= 2
        assert metrics['invitations']['used'] >= 1
        assert metrics['feedback']['total'] >= 1
        assert metrics['support']['critical_or_high_open'] >= 1

        # 2. Acceso denegado para usuario no administrador
        self.client.force_authenticate(user=self.regular_user)
        res_forbidden = self.client.get('/api/v1/beta/admin/metrics/')
        assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # 3. Acceso autorizado para administrador
        self.client.force_authenticate(user=self.admin_user)
        res_ok = self.client.get('/api/v1/beta/admin/metrics/')
        assert res_ok.status_code == status.HTTP_200_OK
        data = res_ok.json()
        assert 'invitations' in data
        assert 'activation_rate_pct' in data['invitations']
        assert 'feedback' in data
        assert 'support' in data

    def test_beta_alerts_service_and_endpoint(self):
        """Verifica el registro y triaje de alertas de incidencias críticas."""
        # 1. Crear feedback de tipo BUG mediante el endpoint formal (dispara el hook de alerta)
        self.client.force_authenticate(user=self.regular_user)
        bug_payload = {
            "category": BetaFeedbackCategory.BUG,
            "title": "Bloqueo al importar libros",
            "description": "La importación de archivos CSV se queda colgada indefinidamente.",
            "page_url": "http://localhost:8000/import",
        }
        res_fb = self.client.post('/api/v1/beta/feedback/', bug_payload, format='json')
        assert res_fb.status_code == status.HTTP_201_CREATED

        # 2. Crear ticket urgente mediante endpoint formal (dispara el hook de alerta)
        ticket_payload = {
            "subject": "Incidencia de seguridad",
            "message": "Comprobación urgente requerida en perfil de usuario.",
            "category": "technical",
            "priority": "critical",
        }
        res_tk = self.client.post('/api/v1/beta/support/', ticket_payload, format='json')
        assert res_tk.status_code == status.HTTP_201_CREATED

        # 3. Verificar servicio de alertas
        alerts = BetaAlertsService.get_active_alerts()
        assert len(alerts) >= 2
        assert any(a['title'] == "Bloqueo al importar libros" for a in alerts)
        assert any(a['title'] == "Incidencia de seguridad" for a in alerts)

        # 4. Endpoint de alertas protegido
        self.client.force_authenticate(user=self.regular_user)
        res_no = self.client.get('/api/v1/beta/admin/alerts/')
        assert res_no.status_code == status.HTTP_403_FORBIDDEN

        self.client.force_authenticate(user=self.admin_user)
        res_yes = self.client.get('/api/v1/beta/admin/alerts/')
        assert res_yes.status_code == status.HTTP_200_OK
        data_alerts = res_yes.json()
        assert data_alerts['count'] >= 2
        assert isinstance(data_alerts['alerts'], list)

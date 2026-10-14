"""
Suite de pruebas para la Fase E2 — Soft Launch y Monitorización (Roadmap v2.0 Bloque E).

Verifica:
1. test_controlled_registration_and_cohort_activation: Registro controlado, validación de invitaciones y cambio de modo de plataforma.
2. test_beta_feedback_submission_and_categorization: Envío de feedback categorizado, alerta de bug y triaje por administración.
3. test_support_ticket_lifecycle: Ciclo de vida completo de tickets de soporte (creación, listado de usuario, resolución admin y permisos).
4. test_system_metrics_and_alert_evaluator_health: Métricas de cohorte y servicio de alertas críticas sin falsos positivos.
5. test_rollback_guide_and_templates_integrity: Existencia y contenido de la guía de rollback y plantillas de comunicación.
"""

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
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
    SupportTicketCategory,
    SupportTicketPriority,
    SupportTicketStatus,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def e2_environment(db):
    user = User.objects.create_user(username="beta_tester", email="tester@test.com", password="password123")
    admin_user = User.objects.create_user(username="beta_admin", email="admin@test.com", password="password123", is_staff=True)
    invitation = BetaInvitation.objects.create(
        code="SOFTLAUNCH2026",
        created_by=admin_user,
        max_uses=10,
        uses_count=2,
        is_active=True,
    )
    return {
        "user": user,
        "admin_user": admin_user,
        "invitation": invitation,
    }


@pytest.mark.django_db
class TestPhaseE2SoftLaunchMonitoring:

    def test_controlled_registration_and_cohort_activation(self, api_client, e2_environment):
        """
        Verifica el comportamiento de las feature flags de registro controlado y la validación
        de códigos de invitación para la cohorte del soft launch.
        """
        invitation = e2_environment["invitation"]

        # 1. Modo closed_beta cuando se requiere invitación
        with override_settings(REQUIRE_BETA_INVITATION=True, PUBLIC_REGISTRATION_ENABLED=True):
            res = api_client.get("/api/v1/beta/registration-status/")
            assert res.status_code == status.HTTP_200_OK
            assert res.data["mode"] == "closed_beta"
            assert res.data["require_invitation"] is True

        # 2. Modo public cuando no se requiere invitación y registro público está activo
        with override_settings(REQUIRE_BETA_INVITATION=False, PUBLIC_REGISTRATION_ENABLED=True):
            res_pub = api_client.get("/api/v1/beta/registration-status/")
            assert res_pub.status_code == status.HTTP_200_OK
            assert res_pub.data["mode"] == "public"
            assert res_pub.data["public_registration_enabled"] is True

        # 3. Modo maintenance cuando el registro público está desactivado
        with override_settings(REQUIRE_BETA_INVITATION=False, PUBLIC_REGISTRATION_ENABLED=False):
            res_maint = api_client.get("/api/v1/beta/registration-status/")
            assert res_maint.status_code == status.HTTP_200_OK
            assert res_maint.data["mode"] == "maintenance"

        # 4. Verificación de código de invitación válido
        res_verify = api_client.post(
            "/api/v1/beta/invitations/verify/",
            {"code": invitation.code},
            format="json",
        )
        assert res_verify.status_code == status.HTTP_200_OK
        assert res_verify.data["valid"] is True
        assert res_verify.data["uses_remaining"] == 8

        # 5. Código inválido retorna 400
        res_inv = api_client.post(
            "/api/v1/beta/invitations/verify/",
            {"code": "CODIGO_FALSO_123"},
            format="json",
        )
        assert res_inv.status_code == status.HTTP_400_BAD_REQUEST

    def test_beta_feedback_submission_and_categorization(self, api_client, e2_environment):
        """
        Verifica el canal de feedback in-app: envío categorizado, captura de contexto
        de dispositivo/página y triaje administrativo.
        """
        user = e2_environment["user"]
        admin_user = e2_environment["admin_user"]

        api_client.force_authenticate(user=user)

        # 1. Usuario anota un bug con contexto
        feedback_payload = {
            "title": "Error al cargar portadas en modo oscuro",
            "description": "Las portadas no renderizan el fallback correctamente en dark mode.",
            "category": BetaFeedbackCategory.BUG,
            "rating": 3,
            "page_url": "/books/123",
            "device_info": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }
        res_submit = api_client.post("/api/v1/beta/feedback/", feedback_payload, format="json")
        assert res_submit.status_code == status.HTTP_201_CREATED
        feedback_id = res_submit.data["id"]

        fb_db = BetaFeedback.objects.get(id=feedback_id)
        assert fb_db.user == user
        assert fb_db.category == BetaFeedbackCategory.BUG
        assert fb_db.status == BetaFeedbackStatus.NEW

        # 2. Admin lista el feedback filtrando por categoría
        api_client.force_authenticate(user=admin_user)
        res_list = api_client.get(f"/api/v1/beta/admin/feedback/?category={BetaFeedbackCategory.BUG}")
        assert res_list.status_code == status.HTTP_200_OK
        ids = [item["id"] for item in res_list.data["results"]]
        assert feedback_id in ids

        # 3. Admin actualiza estado del triaje a IN_REVIEW
        res_patch = api_client.patch(
            f"/api/v1/beta/admin/feedback/{feedback_id}/",
            {"status": BetaFeedbackStatus.IN_REVIEW, "admin_notes": "Reproducido en staging. Asignado a frontend."},
            format="json",
        )
        assert res_patch.status_code == status.HTTP_200_OK
        assert res_patch.data["status"] == BetaFeedbackStatus.IN_REVIEW

    def test_support_ticket_lifecycle(self, api_client, e2_environment):
        """
        Verifica el ciclo de vida de tickets de soporte: apertura, consulta por el usuario,
        intervención y resolución por parte de administración y control de acceso.
        """
        user = e2_environment["user"]
        admin_user = e2_environment["admin_user"]

        # 1. Usuario autenticado abre un ticket técnico urgente
        api_client.force_authenticate(user=user)
        ticket_payload = {
            "subject": "Problema con la sincronización de lectura",
            "message": "El progreso de lectura no se refleja en mi estantería de libros.",
            "category": SupportTicketCategory.TECHNICAL,
            "priority": SupportTicketPriority.HIGH,
        }
        res_create = api_client.post("/api/v1/beta/support/", ticket_payload, format="json")
        assert res_create.status_code == status.HTTP_201_CREATED
        ticket_id = res_create.data["id"]

        ticket_db = SupportTicket.objects.get(id=ticket_id)
        assert ticket_db.user == user
        assert ticket_db.status == SupportTicketStatus.OPEN
        assert ticket_db.priority == SupportTicketPriority.HIGH

        # 2. Usuario consulta su listado personal de tickets
        res_my = api_client.get("/api/v1/beta/support/my/")
        assert res_my.status_code == status.HTTP_200_OK
        assert any(t["id"] == ticket_id for t in res_my.data["results"])

        # 3. Usuario estándar NO puede acceder a endpoints de administración de tickets -> 403
        res_unauth_admin = api_client.get("/api/v1/beta/admin/support/")
        assert res_unauth_admin.status_code == status.HTTP_403_FORBIDDEN

        # 4. Admin accede y resuelve el ticket
        api_client.force_authenticate(user=admin_user)
        res_admin_list = api_client.get("/api/v1/beta/admin/support/")
        assert res_admin_list.status_code == status.HTTP_200_OK

        res_resolve = api_client.patch(
            f"/api/v1/beta/admin/support/{ticket_id}/",
            {
                "status": SupportTicketStatus.RESOLVED,
                "resolution_notes": "Corregido bloqueo en worker Celery de recálculo de progreso.",
            },
            format="json",
        )
        assert res_resolve.status_code == status.HTTP_200_OK
        assert res_resolve.data["status"] == SupportTicketStatus.RESOLVED

    def test_system_metrics_and_alert_evaluator_health(self, e2_environment):
        """
        Verifica que el servicio de telemetría de cohorte calcule las métricas operativas
        y que el despachador de alertas identifique incidencias críticas sin falsos positivos.
        """
        user = e2_environment["user"]

        # Crear datos de prueba
        BetaFeedback.objects.create(
            user=user,
            title="Sugerencia de filtro",
            description="Añadir filtro por idioma.",
            category=BetaFeedbackCategory.MISSING_FEATURE,
            status=BetaFeedbackStatus.NEW,
        )
        urgent_ticket = SupportTicket.objects.create(
            user=user,
            subject="Caída de inicio de sesión",
            message="500 Internal Server Error al ingresar credenciales.",
            category=SupportTicketCategory.ACCOUNT,
            priority=SupportTicketPriority.CRITICAL,
            status=SupportTicketStatus.OPEN,
        )
        normal_ticket = SupportTicket.objects.create(
            user=user,
            subject="Duda de configuración",
            message="¿Cómo cambio mi avatar?",
            category=SupportTicketCategory.OTHER,
            priority=SupportTicketPriority.LOW,
            status=SupportTicketStatus.OPEN,
        )

        # 1. Evaluación de métricas consolidadas
        metrics = BetaMetricsService.get_cohort_summary_metrics()
        assert "invitations" in metrics
        assert "activation_rate_pct" in metrics["invitations"]
        assert "feedback" in metrics
        assert "support" in metrics
        assert metrics["support"]["total"] >= 2
        assert metrics["support"]["by_priority"].get(SupportTicketPriority.CRITICAL, 0) >= 1

        # 2. Evaluación de alertas críticas
        # Ticket crítico debe activar alerta (retorna True)
        assert BetaAlertsService.process_support_ticket_submission(urgent_ticket) is True
        # Ticket de baja prioridad no debe disparar alerta (retorna False)
        assert BetaAlertsService.process_support_ticket_submission(normal_ticket) is False

    def test_rollback_guide_and_templates_integrity(self):
        """
        Verifica la existencia física, integridad y consistencia del manual de rollback
        y las plantillas de comunicación de incidentes.
        """
        guide_path = Path(settings.BASE_DIR) / "docs" / "devops" / "rollback_and_incident_communication_guide.md"
        assert guide_path.exists(), f"El archivo de guía no existe en: {guide_path}"

        content = guide_path.read_text(encoding="utf-8")
        assert "SEV-1" in content
        assert "restore_db.sh" in content
        assert "verify_restore_integrity" in content
        assert "Plantilla 1: Notificación Inicial de Incidencia" in content
        assert "Plantilla 2: Actualización de Mitigación" in content
        assert "Plantilla 3: Notificación de Resolución" in content
        assert "Plantilla 4: Resumen Post-Mortem" in content

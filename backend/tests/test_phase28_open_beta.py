import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from analytics.models import ProductAnalyticsEvent, ProductEventType
from analytics.services import AnalyticsService
from beta.models import (
    SupportTicket,
    SupportTicketCategory,
    SupportTicketPriority,
    SupportTicketStatus,
)

User = get_user_model()


@pytest.mark.django_db
class TestPhase28OpenBeta:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='beta_tester1',
            email='beta1@example.com',
            password='StrongPassword123!'
        )
        self.other_user = User.objects.create_user(
            username='beta_tester2',
            email='beta2@example.com',
            password='StrongPassword123!'
        )
        self.admin = User.objects.create_superuser(
            username='admin_open_beta',
            email='admin_open_beta@example.com',
            password='AdminPassword123!'
        )

    def test_retention_metrics_calculation(self):
        """Calcula de forma precisa la retención de cohortes D1, D7 y D30."""
        now = timezone.now()
        base_time = now - timedelta(days=20)

        # Usuario 1: Registrado hace 20 días con actividad D1 y D7
        signup_1 = ProductAnalyticsEvent.objects.create(
            event_type=ProductEventType.SIGNUP,
            user=self.user,
            timestamp=base_time,
        )
        # Actividad D1 (+1.5 días)
        ProductAnalyticsEvent.objects.create(
            event_type=ProductEventType.BOOK_VIEW,
            user=self.user,
            timestamp=base_time + timedelta(days=1, hours=12),
        )
        # Actividad D7 (+7 días)
        ProductAnalyticsEvent.objects.create(
            event_type=ProductEventType.REVIEW_CREATED,
            user=self.user,
            timestamp=base_time + timedelta(days=7),
        )

        # Usuario 2: Registrado hace 20 días sin actividad posterior
        signup_2 = ProductAnalyticsEvent.objects.create(
            event_type=ProductEventType.SIGNUP,
            user=self.other_user,
            timestamp=base_time,
        )

        metrics = AnalyticsService.get_retention_metrics(days=30)
        assert metrics['total_signups'] == 2
        assert metrics['d1_active_users'] == 1
        assert metrics['d1_retention_rate'] == 0.5
        assert metrics['d7_active_users'] == 1
        assert metrics['d7_retention_rate'] == 0.5
        assert metrics['d30_active_users'] == 0
        assert metrics['d30_retention_rate'] == 0.0

    def test_retention_endpoint_admin_permissions(self):
        """El endpoint /api/v1/analytics/retention/ está protegido exclusivamente para administradores."""
        # Anónimo -> 401
        res_anon = self.client.get('/api/v1/analytics/retention/')
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # Usuario estándar -> 403
        self.client.force_authenticate(user=self.user)
        res_user = self.client.get('/api/v1/analytics/retention/')
        assert res_user.status_code == status.HTTP_403_FORBIDDEN

        # Administrador -> 200 OK con payload estructurado
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.get('/api/v1/analytics/retention/?days=15')
        assert res_admin.status_code == status.HTTP_200_OK
        assert 'total_signups' in res_admin.data
        assert 'd1_retention_rate' in res_admin.data
        assert 'd7_retention_rate' in res_admin.data
        assert 'd30_retention_rate' in res_admin.data
        assert res_admin.data['timeframe_days'] == 15

    def test_support_ticket_create_authenticated(self):
        """Un usuario de la beta abierta puede abrir tickets de soporte con diferentes categorías."""
        self.client.force_authenticate(user=self.user)

        payload = {
            'subject': 'Problema al sincronizar biblioteca',
            'message': 'Mis lecturas marcadas como leídas no aparecen actualizadas en el perfil.',
            'category': SupportTicketCategory.TECHNICAL,
            'priority': SupportTicketPriority.HIGH,
        }
        res = self.client.post('/api/v1/beta/support/', payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED, res.data
        assert res.data['subject'] == payload['subject']
        assert res.data['status'] == SupportTicketStatus.OPEN
        assert res.data['priority'] == SupportTicketPriority.HIGH

        ticket = SupportTicket.objects.get(id=res.data['id'])
        assert ticket.user == self.user
        assert ticket.category == SupportTicketCategory.TECHNICAL

    def test_support_ticket_validation_and_permissions(self):
        """Validación de datos obligatorios y bloqueo para anónimos."""
        # Anónimo -> 401
        res_anon = self.client.post('/api/v1/beta/support/', {
            'subject': 'Sin login',
            'message': 'No debería crearse',
        }, format='json')
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # Asunto muy corto (< 3 caracteres)
        self.client.force_authenticate(user=self.user)
        res_short = self.client.post('/api/v1/beta/support/', {
            'subject': 'ab',
            'message': 'Mensaje suficientemente largo para la prueba',
        }, format='json')
        assert res_short.status_code == status.HTTP_400_BAD_REQUEST
        assert 'subject' in res_short.data

    def test_user_list_own_support_tickets_isolation(self):
        """Cada usuario solo puede listar sus propios tickets de soporte."""
        t1 = SupportTicket.objects.create(
            user=self.user,
            subject='Ticket de usuario 1',
            message='Detalle 1',
            status=SupportTicketStatus.OPEN
        )
        t2 = SupportTicket.objects.create(
            user=self.other_user,
            subject='Ticket de usuario 2',
            message='Detalle 2',
            status=SupportTicketStatus.OPEN
        )

        self.client.force_authenticate(user=self.user)
        res = self.client.get('/api/v1/beta/support/my/')
        assert res.status_code == status.HTTP_200_OK
        results = res.data.get('results', res.data)
        ids = [item['id'] for item in results]
        assert t1.id in ids
        assert t2.id not in ids

    def test_admin_support_ticket_triage_and_response(self):
        """Los administradores pueden filtrar, responder y resolver tickets de soporte."""
        ticket = SupportTicket.objects.create(
            user=self.user,
            subject='Consulta de privacidad de datos',
            message='¿Dónde puedo solicitar la exportación de mis lecturas?',
            category=SupportTicketCategory.ACCOUNT,
            status=SupportTicketStatus.OPEN,
            priority=SupportTicketPriority.MEDIUM
        )

        # Usuario estándar intentando acceder a admin -> 403
        self.client.force_authenticate(user=self.user)
        res_user = self.client.get('/api/v1/beta/admin/support/')
        assert res_user.status_code == status.HTTP_403_FORBIDDEN

        # Administrador lista y filtra
        self.client.force_authenticate(user=self.admin)
        res_admin_list = self.client.get('/api/v1/beta/admin/support/?category=account')
        assert res_admin_list.status_code == status.HTTP_200_OK
        results = res_admin_list.data.get('results', res_admin_list.data)
        assert any(item['id'] == ticket.id for item in results)

        # Administrador responde y resuelve
        patch_payload = {
            'status': SupportTicketStatus.RESOLVED,
            'admin_response': 'Puedes solicitar la exportación en Ajustes de Cuenta -> Privacidad -> Exportar Datos RGPD.',
        }
        res_patch = self.client.patch(f'/api/v1/beta/admin/support/{ticket.id}/', patch_payload, format='json')
        assert res_patch.status_code == status.HTTP_200_OK
        assert res_patch.data['status'] == SupportTicketStatus.RESOLVED
        assert res_patch.data['admin_response'] == patch_payload['admin_response']

        ticket.refresh_from_db()
        assert ticket.status == SupportTicketStatus.RESOLVED
        assert ticket.admin_response == patch_payload['admin_response']

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from beta.models import BetaFeedback, BetaFeedbackCategory, BetaFeedbackStatus, BetaInvitation

User = get_user_model()


@pytest.mark.django_db
class TestPhase27ClosedBeta:
    @pytest.fixture(autouse=True)
    def setup_method_fixture(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='tester1',
            email='tester1@example.com',
            password='StrongPassword123!'
        )
        self.other_user = User.objects.create_user(
            username='tester2',
            email='tester2@example.com',
            password='StrongPassword123!'
        )
        self.admin = User.objects.create_superuser(
            username='admin_beta',
            email='admin_beta@example.com',
            password='AdminPassword123!'
        )

    def test_create_beta_feedback_authenticated(self):
        """Un usuario de la beta puede enviar feedback con cualquiera de las categorías del roadmap."""
        self.client.force_authenticate(user=self.user)

        categories = [
            BetaFeedbackCategory.BUG,
            BetaFeedbackCategory.CONFUSING_UX,
            BetaFeedbackCategory.MISSING_FEATURE,
            BetaFeedbackCategory.PERFORMANCE,
            BetaFeedbackCategory.PRIVACY_CONCERN,
            BetaFeedbackCategory.RECOMMENDATION_QUALITY,
            BetaFeedbackCategory.GENERAL_FEEDBACK,
        ]

        for cat in categories:
            payload = {
                'category': cat,
                'title': f'Prueba de feedback {cat}',
                'description': f'Detalle del problema encontrado en categoría {cat}',
                'page_url': f'/books/{cat}/',
                'device_info': 'Mozilla/5.0 Test Chrome',
            }
            res = self.client.post('/api/v1/beta/feedback/', payload, format='json')
            assert res.status_code == status.HTTP_201_CREATED, res.data
            assert res.data['category'] == cat
            assert res.data['title'] == payload['title']

        # Verificar que se crearon los registros vinculados al usuario con estado 'new'
        feedbacks = BetaFeedback.objects.filter(user=self.user)
        assert feedbacks.count() == len(categories)
        assert all(f.status == BetaFeedbackStatus.NEW for f in feedbacks)

    def test_create_beta_feedback_unauthenticated_forbidden(self):
        """Los usuarios anónimos no pueden enviar feedback en el endpoint de beta (requiere autenticación)."""
        payload = {
            'category': 'bug',
            'title': 'Error anónimo',
            'description': 'No debería crearse sin autenticación',
        }
        res = self.client.post('/api/v1/beta/feedback/', payload, format='json')
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_beta_feedback_validation_errors(self):
        """Validación estricta de longitud mínima de título y descripción."""
        self.client.force_authenticate(user=self.user)

        # Título demasiado corto
        res_short_title = self.client.post('/api/v1/beta/feedback/', {
            'category': 'bug',
            'title': 'ab',
            'description': 'Descripción válida suficientemente larga',
        }, format='json')
        assert res_short_title.status_code == status.HTTP_400_BAD_REQUEST
        assert 'title' in res_short_title.data

        # Descripción demasiado corta
        res_short_desc = self.client.post('/api/v1/beta/feedback/', {
            'category': 'bug',
            'title': 'Título válido',
            'description': '123',
        }, format='json')
        assert res_short_desc.status_code == status.HTTP_400_BAD_REQUEST
        assert 'description' in res_short_desc.data

    def test_admin_list_and_filter_beta_feedback(self):
        """Solo los administradores pueden listar y filtrar el feedback de la beta."""
        # Crear feedbacks de prueba
        f_bug = BetaFeedback.objects.create(
            user=self.user,
            category=BetaFeedbackCategory.BUG,
            title='Error en recomendaciones',
            description='Fallo al cargar carrusel',
            status=BetaFeedbackStatus.NEW
        )
        f_perf = BetaFeedback.objects.create(
            user=self.other_user,
            category=BetaFeedbackCategory.PERFORMANCE,
            title='Lentitud en feed',
            description='Tarda más de 2 segundos en cargar',
            status=BetaFeedbackStatus.IN_REVIEW
        )

        # Usuario normal -> 403 Forbidden
        self.client.force_authenticate(user=self.user)
        res_user = self.client.get('/api/v1/beta/admin/feedback/')
        assert res_user.status_code == status.HTTP_403_FORBIDDEN

        # Administrador -> 200 OK con listado completo
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.get('/api/v1/beta/admin/feedback/')
        assert res_admin.status_code == status.HTTP_200_OK
        results = res_admin.data.get('results', res_admin.data)
        assert len(results) >= 2

        # Filtrar por category=bug
        res_filter_cat = self.client.get('/api/v1/beta/admin/feedback/?category=bug')
        results_bug = res_filter_cat.data.get('results', res_filter_cat.data)
        assert all(item['category'] == 'bug' for item in results_bug)

        # Filtrar por status=in_review
        res_filter_status = self.client.get('/api/v1/beta/admin/feedback/?status=in_review')
        results_status = res_filter_status.data.get('results', res_filter_status.data)
        assert all(item['status'] == 'in_review' for item in results_status)

    def test_admin_update_beta_feedback_status_and_notes(self):
        """Los administradores pueden triajar y actualizar el estado y notas del feedback."""
        feedback = BetaFeedback.objects.create(
            user=self.user,
            category=BetaFeedbackCategory.CONFUSING_UX,
            title='El botón de favoritos no parece activo',
            description='Cuesta entender si se guardó el libro',
            status=BetaFeedbackStatus.NEW
        )

        self.client.force_authenticate(user=self.admin)
        update_payload = {
            'status': BetaFeedbackStatus.RESOLVED,
            'admin_notes': 'Añadida microanimación de confirmación en la UI',
        }
        res = self.client.patch(f'/api/v1/beta/admin/feedback/{feedback.id}/', update_payload, format='json')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['status'] == BetaFeedbackStatus.RESOLVED
        assert res.data['admin_notes'] == update_payload['admin_notes']

        feedback.refresh_from_db()
        assert feedback.status == BetaFeedbackStatus.RESOLVED
        assert feedback.admin_notes == update_payload['admin_notes']

    def test_beta_invitation_lifecycle(self):
        """Creación, verificación y agotamiento de invitaciones para la beta cerrada."""
        # 1. Admin crea invitación
        self.client.force_authenticate(user=self.admin)
        invitation_payload = {
            'code': 'BETA-TEST-2026',
            'invited_email': 'beta_reader@example.com',
            'max_uses': 2,
        }
        res_create = self.client.post('/api/v1/beta/admin/invitations/', invitation_payload, format='json')
        assert res_create.status_code == status.HTTP_201_CREATED
        assert res_create.data['code'] == 'BETA-TEST-2026'
        assert res_create.data['is_valid'] is True

        # 2. Verificación pública válida (sin autenticar)
        self.client.force_authenticate(user=None)
        res_verify = self.client.post('/api/v1/beta/invitations/verify/', {
            'code': 'BETA-TEST-2026'
        }, format='json')
        assert res_verify.status_code == status.HTTP_200_OK
        assert res_verify.data['valid'] is True
        assert res_verify.data['uses_remaining'] == 2

        # 3. Consumir usos
        invitation = BetaInvitation.objects.get(code='BETA-TEST-2026')
        assert invitation.use() is True
        assert invitation.uses_count == 1
        assert invitation.is_valid() is True

        assert invitation.use() is True
        assert invitation.uses_count == 2
        assert invitation.is_valid() is False
        assert invitation.is_active is False

        # 4. Verificar código agotado -> 400 Bad Request
        res_verify_exhausted = self.client.post('/api/v1/beta/invitations/verify/', {
            'code': 'BETA-TEST-2026'
        }, format='json')
        assert res_verify_exhausted.status_code == status.HTTP_400_BAD_REQUEST

    def test_beta_invitation_expired(self):
        """Una invitación con fecha de caducidad pasada es rechazada."""
        expired_invitation = BetaInvitation.objects.create(
            code='EXPIRED-CODE-01',
            max_uses=5,
            expires_at=timezone.now() - timedelta(days=1)
        )
        assert expired_invitation.is_valid() is False

        res = self.client.post('/api/v1/beta/invitations/verify/', {
            'code': 'EXPIRED-CODE-01'
        }, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_beta_invitation_nonexistent(self):
        """Un código inexistente devuelve error 400."""
        res = self.client.post('/api/v1/beta/invitations/verify/', {
            'code': 'DOES-NOT-EXIST'
        }, format='json')
        assert res.status_code == status.HTTP_400_BAD_REQUEST

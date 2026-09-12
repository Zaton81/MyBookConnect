"""
Pruebas exhaustivas para la Fase 29: Sistema de Moderación y Jerarquía de Roles.

Cubre:
1. Jerarquía de roles en User (USER, EDITOR, MODERATOR, ADMIN) y retrocompatibilidad.
2. Denuncias de contenido (User, Review, ReviewComment, Message) mediante GenericForeignKey.
3. Validación estricta: prohibición de auto-denuncias y reportes duplicados pendientes.
4. Políticas de visibilidad para contenido moderado (is_moderated=True).
5. Permisos de moderación (IsModeratorOrAdmin).
6. Ejecución de medidas disciplinarias (HIDE_CONTENT, BAN_USER, DISMISS, WARNING).
7. Métricas y estadísticas de la cola de moderación.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment
from messages_app.models import Conversation, Message
from users.models import Report, ReportReason, ReportStatus, UserRole
from users.policies import can_moderate, filter_visible_reviews

User = get_user_model()


@pytest.mark.django_db
class TestPhase29UserRoles:
    """Valida la coherencia del sistema de roles de usuario."""

    def test_default_user_role(self):
        """Un usuario nuevo debe tener el rol USER por defecto."""
        user = User.objects.create_user(username='regular_user', email='reg@test.com', password='pwd')
        assert user.role == UserRole.USER
        assert not user.is_moderator
        assert not user.is_editor_user
        assert not user.is_staff

    def test_moderator_role_properties(self):
        """Un usuario con rol MODERATOR debe tener is_moderator=True."""
        mod = User.objects.create_user(
            username='mod_user',
            email='mod@test.com',
            password='pwd',
            role=UserRole.MODERATOR,
        )
        assert mod.is_moderator
        assert not mod.is_staff
        assert can_moderate(mod)

    def test_backward_compatibility_staff_and_editor(self):
        """is_staff=True mapea a ADMIN y is_editor=True mapea a EDITOR."""
        admin = User.objects.create_user(username='admin_user', email='adm@test.com', password='pwd', is_staff=True)
        assert admin.role == UserRole.ADMIN
        assert admin.is_moderator
        assert admin.is_editor_user

        editor = User.objects.create_user(username='editor_user', email='ed@test.com', password='pwd', is_editor=True)
        assert editor.role == UserRole.EDITOR
        assert editor.is_editor_user
        assert not editor.is_moderator


@pytest.mark.django_db
class TestPhase29ModerationReporting:
    """Valida la creación, filtrado y restricciones en la emisión de denuncias."""

    def setup_method(self):
        self.reporter = User.objects.create_user(username='denunciante', email='rep@test.com', password='pwd')
        self.bad_actor = User.objects.create_user(username='troll_user', email='troll@test.com', password='pwd')
        self.moderator = User.objects.create_user(
            username='moderador',
            email='mod@test.com',
            password='pwd',
            role=UserRole.MODERATOR,
        )

        self.author = Author.objects.create(name='Autor Test')
        self.book = Book.objects.create(title='Libro Denunciable', author=self.author)
        self.review = Review.objects.create(
            user=self.bad_actor,
            book=self.book,
            rating=1,
            text='Contenido con insultos gravísimos y spam no permitido',
        )
        self.comment = ReviewComment.objects.create(
            user=self.bad_actor,
            review=self.review,
            content='Comentario hostil de prueba',
        )

        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.reporter, self.bad_actor)
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.bad_actor,
            text='Mensaje privado amenazante',
        )

        self.client = APIClient()

    def test_report_review_successfully(self):
        """Un usuario autenticado puede denunciar una reseña ilegítima."""
        self.client.force_authenticate(user=self.reporter)
        payload = {
            'target_type': 'review',
            'object_id': self.review.id,
            'reason': ReportReason.HARASSMENT,
            'description': 'Acoso verbal explícito en la reseña',
        }
        res = self.client.post('/api/v1/reports/', payload)
        assert res.status_code == 201
        assert res.data['reason'] == ReportReason.HARASSMENT
        assert res.data['status'] == ReportStatus.OPEN

        report = Report.objects.get(id=res.data['id'])
        assert report.reporter == self.reporter
        assert report.content_object == self.review

    def test_report_user_profile_successfully(self):
        """Un usuario puede denunciar el perfil de otro usuario infractor."""
        self.client.force_authenticate(user=self.reporter)
        payload = {
            'target_type': 'user',
            'object_id': self.bad_actor.id,
            'reason': ReportReason.SPAM,
            'description': 'Cuenta bot publicando enlaces sospechosos',
        }
        res = self.client.post('/api/v1/reports/', payload)
        assert res.status_code == 201
        report = Report.objects.get(id=res.data['id'])
        assert report.content_object == self.bad_actor

    def test_report_comment_and_message(self):
        """Se pueden reportar comentarios y mensajes directos."""
        self.client.force_authenticate(user=self.reporter)

        # Reportar comentario
        res_comment = self.client.post('/api/v1/reports/', {
            'target_type': 'comment',
            'object_id': self.comment.id,
            'reason': ReportReason.HATE_SPEECH,
            'description': 'Incitación al odio',
        })
        assert res_comment.status_code == 201

        # Reportar mensaje
        res_msg = self.client.post('/api/v1/reports/', {
            'target_type': 'message',
            'object_id': self.message.id,
            'reason': ReportReason.HARASSMENT,
            'description': 'Acoso directo',
        })
        assert res_msg.status_code == 201

    def test_prohibit_self_reporting(self):
        """Un usuario no debe poder denunciar su propio contenido o perfil."""
        self.client.force_authenticate(user=self.bad_actor)

        # Intentar reportar su propia reseña
        res = self.client.post('/api/v1/reports/', {
            'target_type': 'review',
            'object_id': self.review.id,
            'reason': ReportReason.SPAM,
        })
        assert res.status_code == 400
        assert 'No puedes denunciar tu propio contenido' in str(res.data)

        # Intentar reportar su propio perfil
        res_user = self.client.post('/api/v1/reports/', {
            'target_type': 'user',
            'object_id': self.bad_actor.id,
            'reason': ReportReason.SPAM,
        })
        assert res_user.status_code == 400
        assert 'No puedes denunciar tu propio contenido' in str(res_user.data)

    def test_prohibit_duplicate_pending_reports(self):
        """No se permite duplicar denuncias pendientes para un mismo objeto."""
        self.client.force_authenticate(user=self.reporter)
        payload = {
            'target_type': 'review',
            'object_id': self.review.id,
            'reason': ReportReason.INAPPROPRIATE,
        }
        res1 = self.client.post('/api/v1/reports/', payload)
        assert res1.status_code == 201

        res2 = self.client.post('/api/v1/reports/', payload)
        assert res2.status_code == 400
        assert 'Ya tienes una denuncia activa en trámite' in str(res2.data)

    def test_unauthenticated_cannot_report(self):
        """Usuarios anónimos no pueden enviar reportes."""
        res = self.client.post('/api/v1/reports/', {
            'target_type': 'review',
            'object_id': self.review.id,
            'reason': ReportReason.SPAM,
        })
        assert res.status_code == 401

    def test_user_reports_list(self):
        """Un usuario puede ver la lista de sus propias denuncias."""
        self.client.force_authenticate(user=self.reporter)
        self.client.post('/api/v1/reports/', {
            'target_type': 'review',
            'object_id': self.review.id,
            'reason': ReportReason.SPOILER,
        })

        res = self.client.get('/api/v1/reports/my/')
        assert res.status_code == 200
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        assert len(data) == 1
        assert data[0]['target_type'] == 'review'


@pytest.mark.django_db
class TestPhase29ModerationQueueAndResolution:
    """Valida la gestión administrativa de la cola de moderación y medidas disciplinarias."""

    def setup_method(self):
        self.regular_user = User.objects.create_user(username='regular', email='reg@test.com', password='pwd')
        self.offender = User.objects.create_user(username='infractor', email='off@test.com', password='pwd')
        self.moderator = User.objects.create_user(
            username='moderador_oficial',
            email='mod@test.com',
            password='pwd',
            role=UserRole.MODERATOR,
        )

        self.author = Author.objects.create(name='Autor X')
        self.book = Book.objects.create(title='Libro Y', author=self.author)
        self.review = Review.objects.create(
            user=self.offender,
            book=self.book,
            rating=1,
            text='Reseña ofensiva a ser moderada',
        )

        # Crear reporte previo
        self.client = APIClient()
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.post('/api/v1/reports/', {
            'target_type': 'review',
            'object_id': self.review.id,
            'reason': ReportReason.HARASSMENT,
            'description': 'Acoso claro',
        })
        self.report_id = res.data['id']

    def test_regular_user_forbidden_from_admin_reports(self):
        """Un usuario común no puede acceder a los endpoints administrativos de moderación."""
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get('/api/v1/admin/reports/')
        assert res.status_code == 403

        res_detail = self.client.get(f'/api/v1/admin/reports/{self.report_id}/')
        assert res_detail.status_code == 403

    def test_moderator_can_list_and_filter_reports(self):
        """Un moderador puede inspeccionar la cola y aplicar filtros."""
        self.client.force_authenticate(user=self.moderator)
        res = self.client.get('/api/v1/admin/reports/?status=OPEN&reason=HARASSMENT')
        assert res.status_code == 200
        data = res.data if isinstance(res.data, list) else res.data.get('results', [])
        assert len(data) == 1
        assert data[0]['id'] == self.report_id
        assert data[0]['target_type'] == 'review'

    def test_resolve_report_with_hide_content(self):
        """
        Al resolver con HIDE_CONTENT:
        - La reseña se marca is_moderated=True.
        - Desaparece de filter_visible_reviews para usuarios comunes.
        - Permanece visible para moderadores/staff.
        """
        self.client.force_authenticate(user=self.moderator)
        payload = {
            'status': ReportStatus.RESOLVED,
            'action_taken': 'HIDE_CONTENT',
            'resolution_notes': 'Contenido no apto para la comunidad.',
        }
        res = self.client.patch(f'/api/v1/admin/reports/{self.report_id}/', payload)
        assert res.status_code == 200
        assert res.data['status'] == ReportStatus.RESOLVED
        assert res.data['action_taken'] == 'HIDE_CONTENT'
        assert res.data['resolved_by_username'] == self.moderator.username

        # Comprobar que la reseña quedó moderada
        self.review.refresh_from_db()
        assert self.review.is_moderated is True

        # Visibilidad según políticas
        visible_for_regular = filter_visible_reviews(self.regular_user, Review.objects.all())
        assert not visible_for_regular.filter(id=self.review.id).exists()

        visible_for_moderator = filter_visible_reviews(self.moderator, Review.objects.all())
        assert visible_for_moderator.filter(id=self.review.id).exists()

    def test_resolve_report_with_ban_user(self):
        """Al resolver con BAN_USER, la cuenta del usuario infractor se desactiva."""
        # Crear reporte sobre el usuario infractor
        self.client.force_authenticate(user=self.regular_user)
        res_rep = self.client.post('/api/v1/reports/', {
            'target_type': 'user',
            'object_id': self.offender.id,
            'reason': ReportReason.SPAM,
        })
        user_report_id = res_rep.data['id']

        self.client.force_authenticate(user=self.moderator)
        payload = {
            'status': ReportStatus.RESOLVED,
            'action_taken': 'BAN_USER',
            'resolution_notes': 'Spam recurrente, cuenta suspendida permanentemente.',
        }
        res = self.client.patch(f'/api/v1/admin/reports/{user_report_id}/', payload)
        assert res.status_code == 200

        self.offender.refresh_from_db()
        assert self.offender.is_active is False

    def test_reject_report(self):
        """Al rechazar la denuncia (REJECTED), el contenido permanece intacto."""
        self.client.force_authenticate(user=self.moderator)
        payload = {
            'status': ReportStatus.REJECTED,
            'action_taken': 'DISMISS',
            'resolution_notes': 'No se aprecian faltas a las directrices de comunidad.',
        }
        res = self.client.patch(f'/api/v1/admin/reports/{self.report_id}/', payload)
        assert res.status_code == 200
        assert res.data['status'] == ReportStatus.REJECTED

        self.review.refresh_from_db()
        assert self.review.is_moderated is False

    def test_moderation_stats_endpoint(self):
        """El endpoint /api/v1/admin/reports/stats/ provee recuentos agregados."""
        self.client.force_authenticate(user=self.moderator)
        res = self.client.get('/api/v1/admin/reports/stats/')
        assert res.status_code == 200
        assert 'total' in res.data
        assert 'by_status' in res.data
        assert 'by_reason' in res.data
        assert res.data['total'] >= 1

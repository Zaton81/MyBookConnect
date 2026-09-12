"""
Pruebas exhaustivas para la Fase 30: Sistema de Auditoría y AuditLog.

Cubre:
1. Servicio centralizado log_audit y tolerancia a fallos.
2. Registro automático de cambios de roles y baneo de usuarios.
3. Registro automático de bloqueos y desbloqueos sociales.
4. Registro automático de resoluciones de expedientes de moderación.
5. Registro automático de borrado de contenido del catálogo (libros/autores).
6. Restricción estricta de permisos (exclusivo para ADMIN / Superusuario).
7. Filtros de búsqueda y endpoint de estadísticas agregadas.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, Review
from users.audit_service import log_audit
from users.models import AuditAction, AuditLog, Report, ReportReason, ReportStatus, UserRole

User = get_user_model()


@pytest.mark.django_db
class TestPhase30AuditService:
    """Valida el funcionamiento del servicio centralizado de auditoría."""

    def setup_method(self):
        self.admin = User.objects.create_user(
            username='admin_audit',
            email='admin@test.com',
            password='pwd',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.target_user = User.objects.create_user(
            username='lector_target',
            email='target@test.com',
            password='pwd',
        )

    def test_direct_audit_logging(self):
        """Verifica la persistencia de un evento de auditoría con todos sus metadatos."""
        log_entry = log_audit(
            action=AuditAction.SECURITY_PASSWORD_CHANGE,
            actor=self.admin,
            target=self.target_user,
            ip_address='192.168.1.50',
            user_agent='Mozilla/5.0 TestBrowser',
            metadata={'reason': 'solicitud de usuario', 'forced': False},
        )
        assert log_entry is not None
        assert log_entry.action == AuditAction.SECURITY_PASSWORD_CHANGE
        assert log_entry.actor == self.admin
        assert log_entry.content_object == self.target_user
        assert 'Usuario @lector_target' in log_entry.target_repr
        assert log_entry.ip_address == '192.168.1.50'
        assert log_entry.metadata.get('reason') == 'solicitud de usuario'

    def test_audit_service_safe_exception_handling(self):
        """Si un parámetro causa un error inesperado, no debe propagar excepción."""
        # Pasar target con objeto sin atributos de modelo
        result = log_audit(
            action=AuditAction.OTHER,
            target=None,
            metadata={'info': 'test'},
        )
        assert result is not None
        assert result.action == AuditAction.OTHER


@pytest.mark.django_db
class TestPhase30AuditIntegrations:
    """Valida la captura automática de eventos de auditoría en endpoints sensibles."""

    def setup_method(self):
        self.admin = User.objects.create_user(
            username='super_admin',
            email='super@test.com',
            password='pwd',
            role=UserRole.ADMIN,
            is_superuser=True,
            is_staff=True,
        )
        self.moderator = User.objects.create_user(
            username='mod_user',
            email='mod@test.com',
            password='pwd',
            role=UserRole.MODERATOR,
        )
        self.user_a = User.objects.create_user(username='user_alpha', email='alpha@test.com', password='pwd')
        self.user_b = User.objects.create_user(username='user_beta', email='beta@test.com', password='pwd')

        self.author = Author.objects.create(name='Autor Auditoría')
        self.book = Book.objects.create(title='Libro de Auditoría', author=self.author)

        self.client = APIClient()

    def test_role_change_creates_audit_log(self):
        """Modificar el rol de un usuario debe generar un evento ROLE_CHANGE con metadata."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.patch(
            f'/api/v1/admin/users/{self.user_a.id}/',
            {'role': UserRole.MODERATOR},
            format='json',
        )
        assert res.status_code == 200

        log = AuditLog.objects.filter(action=AuditAction.ROLE_CHANGE, object_id=self.user_a.id).first()
        assert log is not None
        assert log.actor == self.admin
        assert log.metadata.get('old_role') == UserRole.USER
        assert log.metadata.get('new_role') == UserRole.MODERATOR

    def test_user_ban_and_unban_creates_audit_log(self):
        """Bloquear y desbloquear una cuenta desde admin genera USER_BAN y USER_UNBAN."""
        self.client.force_authenticate(user=self.admin)

        # Bloquear
        res_ban = self.client.patch(
            f'/api/v1/admin/users/{self.user_a.id}/',
            {'is_active': False},
            format='json',
        )
        assert res_ban.status_code == 200
        ban_log = AuditLog.objects.filter(action=AuditAction.USER_BAN, object_id=self.user_a.id).first()
        assert ban_log is not None
        assert ban_log.actor == self.admin

        # Desbloquear
        res_unban = self.client.patch(
            f'/api/v1/admin/users/{self.user_a.id}/',
            {'is_active': True},
            format='json',
        )
        assert res_unban.status_code == 200
        unban_log = AuditLog.objects.filter(action=AuditAction.USER_UNBAN, object_id=self.user_a.id).first()
        assert unban_log is not None
        assert unban_log.actor == self.admin

    def test_social_block_and_unblock_creates_audit_log(self):
        """El bloqueo y desbloqueo mutuo entre usuarios genera eventos de auditoría."""
        self.client.force_authenticate(user=self.user_a)

        # Bloquear
        res_block = self.client.post(f'/api/v1/users/{self.user_b.id}/block/')
        assert res_block.status_code == 200

        block_log = AuditLog.objects.filter(action=AuditAction.USER_BLOCK, object_id=self.user_b.id).first()
        assert block_log is not None
        assert block_log.actor == self.user_a

        # Desbloquear
        res_unblock = self.client.post(f'/api/v1/users/{self.user_b.id}/unblock/')
        assert res_unblock.status_code == 200

        unblock_log = AuditLog.objects.filter(action=AuditAction.USER_UNBLOCK, object_id=self.user_b.id).first()
        assert unblock_log is not None
        assert unblock_log.actor == self.user_a

    def test_moderation_resolution_creates_audit_log(self):
        """Resolver una denuncia disciplinaria genera MODERATION_RESOLVE con metadatos."""
        review = Review.objects.create(user=self.user_b, book=self.book, rating=1, text='Troll review')
        report = Report.objects.create(
            reporter=self.user_a,
            content_object=review,
            reason=ReportReason.HARASSMENT,
            description='Acoso sistemático',
        )

        self.client.force_authenticate(user=self.moderator)
        res = self.client.patch(
            f'/api/v1/admin/reports/{report.id}/',
            {
                'status': ReportStatus.RESOLVED,
                'action_taken': 'HIDE_CONTENT',
                'resolution_notes': 'Reseña ocultada por directrices de comunidad.',
            },
            format='json',
        )
        assert res.status_code == 200

        mod_log = AuditLog.objects.filter(action=AuditAction.MODERATION_RESOLVE, object_id=report.id).first()
        assert mod_log is not None
        assert mod_log.actor == self.moderator
        assert mod_log.metadata.get('action_taken') == 'HIDE_CONTENT'
        assert mod_log.metadata.get('status') == ReportStatus.RESOLVED

    def test_content_deletion_creates_audit_log(self):
        """Eliminar un libro desde el panel de catálogo genera CONTENT_DELETE."""
        book_to_delete = Book.objects.create(title='Libro a Borrar', author=self.author)
        book_id = book_to_delete.id

        self.client.force_authenticate(user=self.admin)
        res = self.client.delete(f'/api/v1/admin/books/{book_id}/')
        assert res.status_code == 204

        del_log = AuditLog.objects.filter(action=AuditAction.CONTENT_DELETE, object_id=book_id).first()
        assert del_log is not None
        assert del_log.actor == self.admin
        assert del_log.metadata.get('deleted_type') == 'Book'
        assert 'Libro a Borrar' in del_log.metadata.get('title', '')


@pytest.mark.django_db
class TestPhase30AuditPermissionsAndViews:
    """Valida los permisos estrictos y filtros de las vistas de auditoría."""

    def setup_method(self):
        self.admin = User.objects.create_user(
            username='admin_viewer',
            email='adm@test.com',
            password='pwd',
            role=UserRole.ADMIN,
            is_staff=True,
        )
        self.moderator = User.objects.create_user(
            username='mod_viewer',
            email='mod@test.com',
            password='pwd',
            role=UserRole.MODERATOR,
        )
        self.regular_user = User.objects.create_user(
            username='regular_viewer',
            email='reg@test.com',
            password='pwd',
            role=UserRole.USER,
        )

        # Crear algunos logs previos
        log_audit(action=AuditAction.ROLE_CHANGE, actor=self.admin, metadata={'test': 1})
        log_audit(action=AuditAction.USER_BAN, actor=self.admin, metadata={'test': 2})

        self.client = APIClient()

    def test_permissions_admin_only(self):
        """Solo ADMIN o Superusuarios pueden acceder a los logs de auditoría."""
        # Usuario regular -> 403
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get('/api/v1/admin/audit-logs/')
        assert res.status_code == 403

        # Moderador no ADMIN -> 403
        self.client.force_authenticate(user=self.moderator)
        res_mod = self.client.get('/api/v1/admin/audit-logs/')
        assert res_mod.status_code == 403

        # Administrador -> 200
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.get('/api/v1/admin/audit-logs/')
        assert res_admin.status_code == 200
        assert 'results' in res_admin.data
        assert res_admin.data['count'] >= 2

    def test_audit_logs_filtering(self):
        """Permite filtrar por tipo de acción."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get(f'/api/v1/admin/audit-logs/?action={AuditAction.ROLE_CHANGE}')
        assert res.status_code == 200
        results = res.data.get('results', [])
        assert all(item['action'] == AuditAction.ROLE_CHANGE for item in results)

    def test_audit_stats_endpoint(self):
        """Endpoint /api/v1/admin/audit-logs/stats/ retorna recuentos agregados."""
        self.client.force_authenticate(user=self.admin)
        res = self.client.get('/api/v1/admin/audit-logs/stats/')
        assert res.status_code == 200
        assert 'total' in res.data
        assert 'last_24h' in res.data
        assert 'by_action' in res.data
        assert res.data['total'] >= 2

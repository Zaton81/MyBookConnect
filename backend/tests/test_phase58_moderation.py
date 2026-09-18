import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment
from messages_app.models import Conversation, Message
from users.models import AuditAction, AuditLog, Report, ReportReason, ReportStatus, UserRole

User = get_user_model()


@pytest.mark.django_db
class TestPhase58Moderation:
    def setup_method(self):
        self.client = APIClient()

        # Administrador / Moderador
        self.moderator = User.objects.create_user(
            username='mod_alicia',
            email='alicia_mod@example.com',
            password='Password123!',
            role=UserRole.MODERATOR,
            is_staff=True,
        )

        # Superadministrador
        self.admin_boss = User.objects.create_superuser(
            username='admin_boss',
            email='boss@example.com',
            password='Password123!',
            role=UserRole.ADMIN,
        )

        # Usuarios regulares
        self.user_alice = User.objects.create_user(
            username='alice_reader',
            email='alice@example.com',
            password='Password123!',
        )
        self.user_bob = User.objects.create_user(
            username='bob_troll',
            email='bob@example.com',
            password='Password123!',
        )
        self.user_charlie = User.objects.create_user(
            username='charlie_writer',
            email='charlie@example.com',
            password='Password123!',
        )

        # Catálogo de prueba
        self.author = Author.objects.create(name='Jorge Luis Borges', biography='Escritor argentino.')
        self.book = Book.objects.create(
            title='Ficciones',
            author=self.author,
            isbn='9788420633121',
            average_rating=4.9,
        )

        # Reseña de Bob
        self.review_bob = Review.objects.create(
            user=self.user_bob,
            book=self.book,
            rating=2,
            title='Mala lectura',
            text='Texto controvertido de Bob',
        )

        # Reseña de Charlie
        self.review_charlie = Review.objects.create(
            user=self.user_charlie,
            book=self.book,
            rating=9,
            title='Obra maestra',
            text='Análisis detallado de Ficciones',
        )

        # Comentario de Bob en reseña de Charlie
        self.comment_bob = ReviewComment.objects.create(
            user=self.user_bob,
            review=self.review_charlie,
            content='Comentario provocador de Bob',
        )

    # -------------------------------------------------------------------------
    # 1. SOCIAL MUTE & UNMUTE (Herramienta 'mute' entre usuarios)
    # -------------------------------------------------------------------------
    def test_social_mute_and_unmute(self):
        self.client.force_authenticate(user=self.user_alice)

        # Alice silencia a Bob
        res = self.client.post(f'/api/v1/users/{self.user_bob.id}/mute/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['is_muted'] is True
        assert self.user_alice.muted_users.filter(id=self.user_bob.id).exists()

        # Alice no puede silenciarse a sí misma
        res_self = self.client.post(f'/api/v1/users/{self.user_alice.id}/mute/')
        assert res_self.status_code == status.HTTP_400_BAD_REQUEST

        # Al consultar el detalle de Bob, Alice ve is_muted=True
        res_bob = self.client.get(f'/api/v1/users/{self.user_bob.id}/')
        assert res_bob.status_code == status.HTTP_200_OK
        assert res_bob.data.get('is_muted') is True

        # Alice lista reseñas del libro: la reseña de Bob queda oculta para ella
        res_reviews = self.client.get(f'/api/v1/reviews/?book={self.book.id}')
        assert res_reviews.status_code == status.HTTP_200_OK
        results = res_reviews.data if isinstance(res_reviews.data, list) else res_reviews.data.get('results', [])
        author_names = [r['user'] for r in results]
        assert 'bob_troll' not in author_names
        assert 'charlie_writer' in author_names

        # Alice consulta comentarios de la reseña de Charlie: el comentario de Bob queda filtrado
        res_comments = self.client.get(f'/api/v1/reviews/{self.review_charlie.id}/comments/')
        assert res_comments.status_code == status.HTTP_200_OK
        comment_authors = [c['user']['username'] for c in res_comments.data]
        assert 'bob_troll' not in comment_authors

        # Alice des-silencia a Bob
        res_unmute = self.client.post(f'/api/v1/users/{self.user_bob.id}/unmute/')
        assert res_unmute.status_code == status.HTTP_200_OK
        assert res_unmute.data['is_muted'] is False
        assert not self.user_alice.muted_users.filter(id=self.user_bob.id).exists()

        # Ahora Alice puede ver la reseña de Bob
        res_reviews_after = self.client.get(f'/api/v1/reviews/?book={self.book.id}')
        results_after = res_reviews_after.data if isinstance(res_reviews_after.data, list) else res_reviews_after.data.get('results', [])
        assert any(r['user'] == 'bob_troll' for r in results_after)

    # -------------------------------------------------------------------------
    # 2. DISCIPLINARY MUTE (Herramienta 'mute' impuesta por moderadores)
    # -------------------------------------------------------------------------
    def test_disciplinary_mute_enforcement(self):
        # El moderador silencia disciplinariamente a Bob por 24 horas
        self.client.force_authenticate(user=self.moderator)
        res_mute = self.client.post(f'/api/v1/admin/moderation/users/{self.user_bob.id}/mute/', {
            'duration_hours': 24,
            'reason': 'Comportamiento hostil reiterado',
        }, format='json')
        assert res_mute.status_code == status.HTTP_200_OK
        assert res_mute.data['is_disciplinary_muted'] is True

        self.user_bob.refresh_from_db()
        assert self.user_bob.is_disciplinary_muted is True
        assert self.user_bob.is_muted() is True

        # Bob intenta publicar una reseña -> 403 Forbidden
        self.client.force_authenticate(user=self.user_bob)
        res_post_rev = self.client.post('/api/v1/reviews/', {
            'book_id': self.book.id,
            'rating': 5,
            'title': 'Intento reseña',
            'text': 'No debería poder publicar',
        })
        assert res_post_rev.status_code == status.HTTP_403_FORBIDDEN
        assert 'silenciada temporalmente' in res_post_rev.data['detail']

        # Bob intenta publicar un comentario -> 403 Forbidden
        res_post_comm = self.client.post(f'/api/v1/reviews/{self.review_charlie.id}/comments/', {
            'content': 'No debería poder comentar',
        })
        assert res_post_comm.status_code == status.HTTP_403_FORBIDDEN

        # Bob intenta enviar un mensaje en chat -> 403 Forbidden
        conv = Conversation.objects.create()
        conv.participants.add(self.user_bob, self.user_alice)
        self.user_bob.following.add(self.user_alice)
        self.user_alice.following.add(self.user_bob)

        res_msg = self.client.post('/api/v1/messages/', {
            'conversation': conv.id,
            'text': 'Mensaje bloqueado por silenciamiento',
        })
        assert res_msg.status_code == status.HTTP_403_FORBIDDEN

        # El moderador levanta el silenciamiento disciplinario
        self.client.force_authenticate(user=self.moderator)
        res_unmute = self.client.post(f'/api/v1/admin/moderation/users/{self.user_bob.id}/unmute/')
        assert res_unmute.status_code == status.HTTP_200_OK
        assert res_unmute.data['is_disciplinary_muted'] is False

        self.user_bob.refresh_from_db()
        assert self.user_bob.is_disciplinary_muted is False

    # -------------------------------------------------------------------------
    # 3. DIRECT HIDE & RESTORE (Herramientas 'hide' y 'restore')
    # -------------------------------------------------------------------------
    def test_direct_hide_and_restore(self):
        self.client.force_authenticate(user=self.moderator)

        # Ocultar reseña
        res_hide = self.client.post('/api/v1/admin/moderation/hide/', {
            'target_type': 'review',
            'target_id': self.review_bob.id,
            'reason': 'Lenguaje inapropiado',
        }, format='json')
        assert res_hide.status_code == status.HTTP_200_OK
        assert res_hide.data['hidden'] is True

        self.review_bob.refresh_from_db()
        assert self.review_bob.is_moderated is True

        # Usuarios anónimos o no-staff no la ven
        self.client.force_authenticate(user=self.user_alice)
        res_rev_list = self.client.get(f'/api/v1/reviews/?book={self.book.id}')
        results = res_rev_list.data if isinstance(res_rev_list.data, list) else res_rev_list.data.get('results', [])
        assert not any(r['id'] == self.review_bob.id for r in results)

        # Restaurar reseña
        self.client.force_authenticate(user=self.moderator)
        res_restore = self.client.post('/api/v1/admin/moderation/restore/', {
            'target_type': 'review',
            'target_id': self.review_bob.id,
        }, format='json')
        assert res_restore.status_code == status.HTTP_200_OK
        assert res_restore.data['hidden'] is False

        self.review_bob.refresh_from_db()
        assert self.review_bob.is_moderated is False

        # Ocultar comentario
        res_hide_comm = self.client.post('/api/v1/admin/moderation/hide/', {
            'target_type': 'comment',
            'target_id': self.comment_bob.id,
        }, format='json')
        assert res_hide_comm.status_code == status.HTTP_200_OK
        self.comment_bob.refresh_from_db()
        assert self.comment_bob.deleted_at is not None

        # Restaurar comentario
        res_res_comm = self.client.post('/api/v1/admin/moderation/restore/', {
            'target_type': 'comment',
            'target_id': self.comment_bob.id,
        }, format='json')
        assert res_res_comm.status_code == status.HTTP_200_OK
        self.comment_bob.refresh_from_db()
        assert self.comment_bob.deleted_at is None

    # -------------------------------------------------------------------------
    # 4. DIRECT BAN & UNBAN (Herramienta 'ban')
    # -------------------------------------------------------------------------
    def test_direct_ban_and_unban(self):
        self.client.force_authenticate(user=self.moderator)

        # Moderador banea a Bob
        res_ban = self.client.post(f'/api/v1/admin/moderation/users/{self.user_bob.id}/ban/', {
            'reason': 'Múltiples infracciones de acoso',
        }, format='json')
        assert res_ban.status_code == status.HTTP_200_OK
        assert res_ban.data['is_active'] is False

        self.user_bob.refresh_from_db()
        assert self.user_bob.is_active is False

        # Moderador no puede auto-suspenderse
        res_self_ban = self.client.post(f'/api/v1/admin/moderation/users/{self.moderator.id}/ban/')
        assert res_self_ban.status_code == status.HTTP_400_BAD_REQUEST

        # Moderador no puede suspender a un superusuario
        res_super_ban = self.client.post(f'/api/v1/admin/moderation/users/{self.admin_boss.id}/ban/')
        assert res_super_ban.status_code == status.HTTP_400_BAD_REQUEST

        # Desbanear a Bob
        res_unban = self.client.post(f'/api/v1/admin/moderation/users/{self.user_bob.id}/unban/')
        assert res_unban.status_code == status.HTTP_200_OK
        assert res_unban.data['is_active'] is True

        self.user_bob.refresh_from_db()
        assert self.user_bob.is_active is True

    # -------------------------------------------------------------------------
    # 5. REPORT & REVIEW (Herramientas 'report' y 'review')
    # -------------------------------------------------------------------------
    def test_report_and_review_workflow(self):
        # Alice reporta la reseña de Bob
        self.client.force_authenticate(user=self.user_alice)
        res_report = self.client.post('/api/v1/reports/', {
            'target_type': 'review',
            'object_id': self.review_bob.id,
            'reason': 'HARASSMENT',
            'description': 'Contiene provocaciones e insultos reiterados',
        }, format='json')
        assert res_report.status_code == status.HTTP_201_CREATED
        report_id = res_report.data['id']

        # El moderador consulta la cola de reportes
        self.client.force_authenticate(user=self.moderator)
        res_queue = self.client.get('/api/v1/admin/reports/')
        assert res_queue.status_code == status.HTTP_200_OK
        assert any(rep['id'] == report_id for rep in res_queue.data['results'])

        # El moderador resuelve el reporte aplicando MUTE_USER_24H
        res_resolve = self.client.patch(f'/api/v1/admin/reports/{report_id}/', {
            'status': 'RESOLVED',
            'action_taken': 'MUTE_USER_24H',
            'resolution_notes': 'Procedente. Se silencia al autor por 24 horas.',
        }, format='json')
        assert res_resolve.status_code == status.HTTP_200_OK
        assert res_resolve.data['status'] == 'RESOLVED'

        # Verificación de que Bob quedó silenciado
        self.user_bob.refresh_from_db()
        assert self.user_bob.is_disciplinary_muted is True

    # -------------------------------------------------------------------------
    # 6. SOCIAL BLOCK (Herramienta 'block')
    # -------------------------------------------------------------------------
    def test_social_block_and_unblock(self):
        self.client.force_authenticate(user=self.user_alice)

        # Alice bloquea a Bob
        res_block = self.client.post(f'/api/v1/users/{self.user_bob.id}/block/')
        assert res_block.status_code == status.HTTP_200_OK
        assert self.user_alice.blocked_users.filter(id=self.user_bob.id).exists()

        # Al consultar detalle de Bob, is_blocked es True
        res_bob = self.client.get(f'/api/v1/users/{self.user_bob.id}/')
        assert res_bob.data.get('is_blocked') is True

        # Alice desbloquea a Bob
        res_unblock = self.client.post(f'/api/v1/users/{self.user_bob.id}/unblock/')
        assert res_unblock.status_code == status.HTTP_200_OK
        assert not self.user_alice.blocked_users.filter(id=self.user_bob.id).exists()

    # -------------------------------------------------------------------------
    # 7. AUDIT LOG TRACEABILITY (Trazabilidad inmutable de todas las acciones)
    # -------------------------------------------------------------------------
    def test_audit_log_traceability(self):
        # Alice silencia socialmente a Bob
        self.client.force_authenticate(user=self.user_alice)
        self.client.post(f'/api/v1/users/{self.user_bob.id}/mute/')
        assert AuditLog.objects.filter(action=AuditAction.USER_MUTE, actor=self.user_alice).exists()

        # Alice des-silencia socialmente a Bob
        self.client.post(f'/api/v1/users/{self.user_bob.id}/unmute/')
        assert AuditLog.objects.filter(action=AuditAction.USER_UNMUTE, actor=self.user_alice).exists()

        # Moderador oculta contenido
        self.client.force_authenticate(user=self.moderator)
        self.client.post('/api/v1/admin/moderation/hide/', {
            'target_type': 'review',
            'target_id': self.review_bob.id,
        }, format='json')
        assert AuditLog.objects.filter(action=AuditAction.CONTENT_HIDE, actor=self.moderator).exists()

        # Moderador silencia disciplinariamente a Bob
        self.client.post(f'/api/v1/admin/moderation/users/{self.user_bob.id}/mute/', {
            'duration_hours': 48,
        }, format='json')
        assert AuditLog.objects.filter(action=AuditAction.MODERATOR_MUTE, actor=self.moderator).exists()

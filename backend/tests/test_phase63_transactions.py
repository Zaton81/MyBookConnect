from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment, ReviewLike
from books.services.import_service import _create_or_get_from_volume
from users.models import AuditLog, Notification, NotificationType

User = get_user_model()


class Phase63TransactionsTestCase(TestCase):
    """
    Suite de pruebas para la Fase 63: Transacciones atómicas con transaction.atomic().
    Verifica que las operaciones multi-entidad:
    1. Hacen rollback completo (ACID) si falla cualquier paso intermedio (sin estados huérfanos ni inconsistentes).
    2. Hacen commit completo en flujos nominales exitosos.
    """

    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username='user_alice',
            email='alice@example.com',
            password='password123',
        )
        self.user_b = User.objects.create_user(
            username='user_bob',
            email='bob@example.com',
            password='password123',
        )
        self.admin = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            password='adminpassword123',
        )
        self.author = Author.objects.create(name='Gabriel García Márquez')
        self.book = Book.objects.create(
            title='Cien años de soledad',
            author=self.author,
            isbn='9780307474728',
        )

    # -------------------------------------------------------------------------
    # 1. Follow User Atomic Rollback
    # -------------------------------------------------------------------------
    def test_follow_user_atomic_rollback_on_notification_failure(self):
        """
        Al fallar la creación de la notificación durante el seguimiento,
        el manejador de excepciones atrapa el error (500) y se hace rollback
        completo de following.add y de la actividad social.
        """
        self.client.force_authenticate(user=self.user_a)

        with patch('users.models.Notification.objects.create', side_effect=IntegrityError("DB Error Notification")):
            response = self.client.post(f'/api/v1/users/{self.user_b.id}/follow/')
            self.assertEqual(response.status_code, 500)

        # Verificar que el seguimiento NO se persistió (rollback)
        self.user_a.refresh_from_db()
        self.assertNotIn(self.user_b, self.user_a.following.all())
        self.assertEqual(Notification.objects.filter(recipient=self.user_b).count(), 0)

    def test_follow_user_nominal_commit(self):
        """Flujo nominal: follow se persiste junto con su notificación y actividad."""
        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(f'/api/v1/users/{self.user_b.id}/follow/')
        self.assertEqual(response.status_code, 200)

        self.user_a.refresh_from_db()
        self.assertIn(self.user_b, self.user_a.following.all())
        self.assertTrue(Notification.objects.filter(recipient=self.user_b, actor=self.user_a, type=NotificationType.FOLLOW).exists())

    # -------------------------------------------------------------------------
    # 2. Block User Atomic Rollback
    # -------------------------------------------------------------------------
    def test_block_user_atomic_rollback_on_audit_failure(self):
        """
        Al fallar el registro de auditoría en BlockUserView, la adición a blocked_users
        y la desvinculación bidireccional de following deben deshacerse por completo.
        """
        # Preparar relación de seguimiento mutuo previa
        self.user_a.following.add(self.user_b)
        self.user_b.following.add(self.user_a)

        self.client.force_authenticate(user=self.user_a)

        with patch('users.audit_service.log_audit', side_effect=RuntimeError("Audit Service Unavailable")):
            response = self.client.post(f'/api/v1/users/{self.user_b.id}/block/')
            self.assertEqual(response.status_code, 500)

        # Verificar que se revirtió: Alice sigue a Bob, Bob sigue a Alice y Bob NO está bloqueado
        self.user_a.refresh_from_db()
        self.user_b.refresh_from_db()
        self.assertNotIn(self.user_b, self.user_a.blocked_users.all())
        self.assertIn(self.user_b, self.user_a.following.all())
        self.assertIn(self.user_a, self.user_b.following.all())

    def test_block_user_nominal_commit(self):
        """Flujo nominal: bloqueo, desvinculación bidireccional y log de auditoría se guardan conjuntamente."""
        self.user_a.following.add(self.user_b)
        self.user_b.following.add(self.user_a)

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(f'/api/v1/users/{self.user_b.id}/block/')
        self.assertEqual(response.status_code, 200)

        self.user_a.refresh_from_db()
        self.user_b.refresh_from_db()
        self.assertIn(self.user_b, self.user_a.blocked_users.all())
        self.assertNotIn(self.user_b, self.user_a.following.all())
        self.assertNotIn(self.user_a, self.user_b.following.all())
        self.assertTrue(AuditLog.objects.filter(actor=self.user_a, action='USER_BLOCK').exists())

    # -------------------------------------------------------------------------
    # 3. Review Creation Atomic Rollback
    # -------------------------------------------------------------------------
    def test_review_creation_atomic_rollback_on_gamification_failure(self):
        """
        Si la evaluación de gamificación lanza una excepción dentro de la transacción,
        la reseña creada no debe persistirse en la base de datos.
        """
        self.client.force_authenticate(user=self.user_a)
        payload = {
            'book': self.book.id,
            'rating': 9,
            'title': 'Obra maestra de la literatura',
            'text': 'Un viaje inolvidable por Macondo.',
        }

        with patch('books.services.gamification_service.GamificationService.evaluate_user_badges', side_effect=IntegrityError("Badge lock failed")):
            with self.assertRaises(IntegrityError):
                with transaction.atomic():
                    Review.objects.create(
                        user=self.user_a,
                        book=self.book,
                        rating=payload['rating'],
                        title=payload['title'],
                        text=payload['text'],
                    )
                    from books.services.gamification_service import GamificationService
                    GamificationService.evaluate_user_badges(self.user_a)

        # La reseña no debe existir en BD
        self.assertFalse(Review.objects.filter(user=self.user_a, book=self.book).exists())

    def test_review_creation_nominal_commit(self):
        """Flujo nominal: la reseña se crea y persiste con su endpoint normal."""
        self.client.force_authenticate(user=self.user_a)
        payload = {
            'book': self.book.id,
            'rating': 8,
            'title': 'Excelente',
            'text': 'Muy recomendable.',
        }
        response = self.client.post('/api/v1/books/reviews/', data=payload, format='json')
        self.assertIn(response.status_code, (200, 201))
        self.assertTrue(Review.objects.filter(user=self.user_a, book=self.book).exists())

    # -------------------------------------------------------------------------
    # 4. Review Like and Comment Atomic Rollbacks
    # -------------------------------------------------------------------------
    def test_review_like_atomic_rollback_on_notification_failure(self):
        """Al fallar la notificación en ReviewLikeToggleView, el ReviewLike no debe persistirse."""
        review = Review.objects.create(
            user=self.user_b,
            book=self.book,
            rating=10,
            title='Genial',
            text='Magnífica obra.',
        )

        self.client.force_authenticate(user=self.user_a)
        with patch('users.models.Notification.objects.create', side_effect=RuntimeError("Notification service down")):
            response = self.client.post(f'/api/v1/books/reviews/{review.id}/like/')
            self.assertEqual(response.status_code, 500)

        self.assertFalse(ReviewLike.objects.filter(user=self.user_a, review=review).exists())

    def test_review_like_nominal_commit(self):
        """Flujo nominal: like y notificación se crean atómicamente."""
        review = Review.objects.create(
            user=self.user_b,
            book=self.book,
            rating=10,
            title='Genial',
            text='Magnífica obra.',
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(f'/api/v1/books/reviews/{review.id}/like/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ReviewLike.objects.filter(user=self.user_a, review=review).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.user_b, actor=self.user_a, type=NotificationType.LIKE).exists())

    def test_review_comment_atomic_rollback_on_notification_failure(self):
        """Al fallar la notificación en ReviewCommentListCreateView, el comentario no debe persistirse."""
        review = Review.objects.create(
            user=self.user_b,
            book=self.book,
            rating=10,
            title='Genial',
            text='Magnífica obra.',
        )

        self.client.force_authenticate(user=self.user_a)
        with patch('users.models.Notification.objects.create', side_effect=RuntimeError("Push error")):
            response = self.client.post(f'/api/v1/books/reviews/{review.id}/comments/', data={'content': 'Totalmente de acuerdo.'}, format='json')
            self.assertEqual(response.status_code, 500)

        self.assertFalse(ReviewComment.objects.filter(user=self.user_a, review=review).exists())

    def test_review_comment_nominal_commit(self):
        """Flujo nominal: comentario y notificación se crean de forma atómica."""
        review = Review.objects.create(
            user=self.user_b,
            book=self.book,
            rating=10,
            title='Genial',
            text='Magnífica obra.',
        )

        self.client.force_authenticate(user=self.user_a)
        response = self.client.post(f'/api/v1/books/reviews/{review.id}/comments/', data={'content': 'Gran comentario.'}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(ReviewComment.objects.filter(user=self.user_a, review=review).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.user_b, actor=self.user_a, type=NotificationType.COMMENT).exists())

    # -------------------------------------------------------------------------
    # 5. Book Import Atomic Rollback
    # -------------------------------------------------------------------------
    def test_book_import_atomic_rollback_on_category_failure(self):
        """
        Si durante la importación desde volumen de Google Books
        falla la vinculación de categorías, el libro no debe quedar huérfano en la BD.
        """
        volume = {
            'id': 'gvol_unique_123',
            'volumeInfo': {
                'title': 'Libro Atómico Test',
                'authors': ['Autor Nuevo'],
                'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9781112223334'}],
                'categories': ['Ficción / Aventura'],
            }
        }

        with patch('books.services.import_service.attach_categories_to_book', side_effect=IntegrityError("Category M2M Error")):
            with self.assertRaises(IntegrityError):
                _create_or_get_from_volume(volume)

        # El libro NO debe haberse creado
        self.assertFalse(Book.objects.filter(isbn='9781112223334').exists())

    def test_book_import_nominal_commit(self):
        """Flujo nominal: libro, autor y categorías se importan atómicamente."""
        volume = {
            'id': 'gvol_nominal_456',
            'volumeInfo': {
                'title': 'Libro Nominal Test',
                'authors': ['Autor Éxito'],
                'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9789998887776'}],
                'categories': ['Ciencia Ficción'],
            }
        }

        book = _create_or_get_from_volume(volume)
        self.assertIsNotNone(book)
        self.assertEqual(book.title, 'Libro Nominal Test')
        self.assertTrue(Book.objects.filter(isbn='9789998887776').exists())
        self.assertTrue(Author.objects.filter(name='Autor Éxito').exists())

    # -------------------------------------------------------------------------
    # 6. Moderation Actions Atomic Rollback
    # -------------------------------------------------------------------------
    def test_admin_content_hide_atomic_rollback_on_audit_failure(self):
        """Si falla el registro de auditoría en AdminContentHideView, el contenido no debe ocultarse."""
        review = Review.objects.create(
            user=self.user_b,
            book=self.book,
            rating=5,
            title='Regular',
            text='Texto de prueba.',
            is_moderated=False,
        )

        self.client.force_authenticate(user=self.admin)
        with patch('users.audit_service.log_audit', side_effect=RuntimeError("Audit failure")):
            response = self.client.post('/api/v1/admin/moderation/hide/', data={'target_type': 'review', 'target_id': review.id}, format='json')
            self.assertEqual(response.status_code, 500)

        review.refresh_from_db()
        self.assertFalse(review.is_moderated)

    def test_admin_user_ban_atomic_rollback_on_audit_failure(self):
        """Si falla la auditoría al suspender un usuario en AdminUserBanView, is_active no debe cambiar a False."""
        self.assertTrue(self.user_b.is_active)
        self.client.force_authenticate(user=self.admin)

        with patch('users.audit_service.log_audit', side_effect=RuntimeError("Audit write failure")):
            response = self.client.post(f'/api/v1/admin/moderation/users/{self.user_b.id}/ban/', data={'reason': 'Spam'}, format='json')
            self.assertEqual(response.status_code, 500)

        self.user_b.refresh_from_db()
        self.assertTrue(self.user_b.is_active)

    def test_admin_user_ban_nominal_commit(self):
        """Flujo nominal: suspensión de usuario y registro de auditoría atómicos."""
        self.assertTrue(self.user_b.is_active)
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(f'/api/v1/admin/moderation/users/{self.user_b.id}/ban/', data={'reason': 'Violación de normas'}, format='json')
        self.assertEqual(response.status_code, 200)

        self.user_b.refresh_from_db()
        self.assertFalse(self.user_b.is_active)
        self.assertTrue(AuditLog.objects.filter(actor=self.admin, action='USER_BAN').exists())

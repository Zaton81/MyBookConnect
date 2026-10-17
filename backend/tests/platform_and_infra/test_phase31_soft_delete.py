import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment
from messages_app.models import Conversation, Message

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(username='user1', email='user1@example.com', password='password123')


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='user2', email='user2@example.com', password='password123')


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(username='staff1', email='staff1@example.com', password='password123', is_staff=True)


@pytest.fixture
def book(db):
    author = Author.objects.create(name='Gabriel García Márquez')
    return Book.objects.create(title='Cien años de soledad', author=author, isbn='9780307474728')


@pytest.fixture
def client_for():
    def _make_client(user):
        c = APIClient()
        if user:
            c.force_authenticate(user=user)
        return c
    return _make_client


@pytest.mark.django_db
class TestSoftDeleteModelBasics:
    """Verifica el comportamiento de SoftDeleteModel, SoftDeleteQuerySet y SoftDeleteManager."""

    def test_review_soft_delete_and_restore(self, test_user, book):
        review = Review.objects.create(user=test_user, book=book, rating=4, title='Excelente', text='Muy bueno')
        assert not review.is_deleted
        assert review.deleted_at is None

        # Borrado lógico mediante delete()
        review.delete()
        review.refresh_from_db()
        assert review.is_deleted
        assert review.deleted_at is not None

        # Manager active() y deleted()
        assert Review.objects.active().filter(id=review.id).count() == 0
        assert Review.objects.deleted().filter(id=review.id).count() == 1

        # Restauración
        review.restore()
        review.refresh_from_db()
        assert not review.is_deleted
        assert review.deleted_at is None
        assert Review.objects.active().filter(id=review.id).count() == 1

    def test_review_hard_delete(self, test_user, book):
        review = Review.objects.create(user=test_user, book=book, rating=5, title='Obra maestra')
        review_id = review.id
        review.delete(hard=True)
        assert Review.all_objects.filter(id=review_id).count() == 0

    def test_review_comment_soft_delete(self, test_user, book):
        review = Review.objects.create(user=test_user, book=book, rating=4)
        comment = ReviewComment.objects.create(user=test_user, review=review, content='Totalmente de acuerdo')
        assert not comment.is_deleted

        comment.delete()
        comment.refresh_from_db()
        assert comment.is_deleted
        assert ReviewComment.objects.active().filter(id=comment.id).count() == 0
        assert ReviewComment.objects.deleted().filter(id=comment.id).count() == 1

        comment.restore()
        comment.refresh_from_db()
        assert not comment.is_deleted

    def test_message_soft_delete(self, test_user, other_user):
        conv, _ = Conversation.get_or_create_direct(test_user, other_user)
        msg = Message.objects.create(conversation=conv, sender=test_user, text='Hola, ¿qué tal?')
        assert not msg.is_deleted

        msg.delete()
        msg.refresh_from_db()
        assert msg.is_deleted
        assert Message.objects.active().filter(id=msg.id).count() == 0
        assert Message.objects.deleted().filter(id=msg.id).count() == 1

        msg.restore()
        msg.refresh_from_db()
        assert not msg.is_deleted

    def test_queryset_bulk_soft_delete_and_restore(self, test_user, other_user, book):
        r1 = Review.objects.create(user=test_user, book=book, rating=4)
        author2 = Author.objects.create(name='Jorge Luis Borges')
        book2 = Book.objects.create(title='Ficciones', author=author2, isbn='9780140186932')
        r2 = Review.objects.create(user=other_user, book=book2, rating=5)

        # Bulk soft delete
        Review.objects.filter(id__in=[r1.id, r2.id]).soft_delete()
        assert Review.objects.active().filter(id__in=[r1.id, r2.id]).count() == 0
        assert Review.objects.deleted().filter(id__in=[r1.id, r2.id]).count() == 2

        # Bulk restore
        Review.objects.filter(id__in=[r1.id, r2.id]).restore()
        assert Review.objects.active().filter(id__in=[r1.id, r2.id]).count() == 2


@pytest.mark.django_db
class TestPartialUniqueConstraint:
    """Verifica que un usuario pueda crear una nueva reseña activa tras haber borrado lógicamente la anterior."""

    def test_can_re_review_after_soft_delete(self, test_user, book):
        r1 = Review.objects.create(user=test_user, book=book, rating=5, text='Primera reseña')
        r1.delete()
        assert r1.is_deleted

        # Debe permitir crear una segunda reseña activa sin error de integridad
        r2 = Review.objects.create(user=test_user, book=book, rating=5, text='Segunda reseña tras releer')
        assert not r2.is_deleted
        assert Review.all_objects.filter(user=test_user, book=book).count() == 2
        assert Review.objects.active().filter(user=test_user, book=book).count() == 1

    def test_active_duplicate_review_raises_integrity_error(self, test_user, book):
        Review.objects.create(user=test_user, book=book, rating=4)
        with pytest.raises(IntegrityError):
            Review.objects.create(user=test_user, book=book, rating=5)


@pytest.mark.django_db
class TestRatingRecalculationWithSoftDelete:
    """Verifica que el promedio de calificación del libro excluya reseñas eliminadas lógicamente."""

    def test_rating_excludes_soft_deleted_reviews(self, test_user, other_user, book):
        r1 = Review.objects.create(user=test_user, book=book, rating=4)
        r2 = Review.objects.create(user=other_user, book=book, rating=2)

        book.refresh_from_db()
        assert book.average_rating == 3.0

        # Eliminar r2 (rating 2) lógicamente
        r2.delete()
        book.refresh_from_db()
        assert book.average_rating == 4.0

        # Restaurar r2
        r2.restore()
        # Disparar actualización de rating
        r2.save()
        book.refresh_from_db()
        assert book.average_rating == 3.0


@pytest.mark.django_db
class TestSoftDeleteAPIEndpoints:
    """Verifica los endpoints REST con respecto al borrado lógico."""

    def test_list_reviews_excludes_soft_deleted(self, client_for, test_user, other_user, book):
        r1 = Review.objects.create(user=test_user, book=book, rating=4, title='Visible')
        r2 = Review.objects.create(user=other_user, book=book, rating=3, title='Eliminada')
        r2.delete()

        client = client_for(test_user)
        response = client.get(f'/api/v1/books/reviews/?book={book.id}')
        assert response.status_code == status.HTTP_200_OK

        results = response.data.get('results', response.data)
        ids = [item['id'] for item in results]
        assert r1.id in ids
        assert r2.id not in ids

    def test_retrieve_soft_deleted_review_returns_404_for_regular_user(self, client_for, test_user, staff_user, book):
        r = Review.objects.create(user=test_user, book=book, rating=4)
        r.delete()

        client = client_for(test_user)
        res = client.get(f'/api/v1/books/reviews/{r.id}/')
        assert res.status_code == status.HTTP_404_NOT_FOUND

        # Staff sí puede acceder si es necesario
        staff_client = client_for(staff_user)
        res_staff = staff_client.get(f'/api/v1/books/reviews/{r.id}/')
        assert res_staff.status_code == status.HTTP_200_OK

    def test_delete_review_api_performs_soft_delete(self, client_for, test_user, book):
        r = Review.objects.create(user=test_user, book=book, rating=5, title='Para borrar')
        client = client_for(test_user)

        res = client.delete(f'/api/v1/books/reviews/{r.id}/')
        assert res.status_code == status.HTTP_204_NO_CONTENT

        r.refresh_from_db()
        assert r.is_deleted
        assert r.deleted_at is not None

    def test_book_detail_and_reviews_count_exclude_soft_deleted(self, client_for, test_user, other_user, book):
        r1 = Review.objects.create(user=test_user, book=book, rating=5)
        r2 = Review.objects.create(user=other_user, book=book, rating=4)
        r2.delete()

        client = client_for(test_user)
        res = client.get(f'/api/v1/books/{book.id}/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['reviews_count'] == 1
        assert res.data['rating_distribution'][5] == 1
        assert res.data['rating_distribution'][4] == 0

    def test_message_api_soft_delete(self, client_for, test_user, other_user):
        conv, _ = Conversation.get_or_create_direct(test_user, other_user)
        msg1 = Message.objects.create(conversation=conv, sender=test_user, text='Mensaje 1')
        msg2 = Message.objects.create(conversation=conv, sender=test_user, text='Mensaje 2')

        client = client_for(test_user)
        # Listar antes de borrar
        res = client.get(f'/api/v1/chat/messages/?conversation={conv.id}')
        assert res.status_code == status.HTTP_200_OK
        ids = [item['id'] for item in res.data['results']]
        assert msg1.id in ids and msg2.id in ids

        # Borrado lógico de msg2 (por moderación o servicio)
        msg2.delete()
        msg2.refresh_from_db()
        assert msg2.is_deleted
        assert msg2.deleted_at is not None

        # Listar mensajes tras el borrado lógico: msg2 no debe aparecer
        res_after = client.get(f'/api/v1/chat/messages/?conversation={conv.id}')
        assert res_after.status_code == status.HTTP_200_OK
        ids_after = [item['id'] for item in res_after.data['results']]
        assert msg1.id in ids_after
        assert msg2.id not in ids_after

        # Comprobar que en la vista de conversaciones el last_message refleje msg1 y no msg2
        conv_res = client.get('/api/v1/chat/conversations/')
        assert conv_res.status_code == status.HTTP_200_OK
        items = conv_res.data['results'] if isinstance(conv_res.data, dict) and 'results' in conv_res.data else conv_res.data
        conv_item = next((c for c in items if c['id'] == conv.id), None)
        assert conv_item is not None
        assert conv_item['last_message']['id'] == msg1.id

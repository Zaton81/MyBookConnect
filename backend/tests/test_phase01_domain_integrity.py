import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    Book,
    ReadingList,
    ReadingListItem,
    Review,
    ReviewLike,
    UserBook,
)
from books.serializers import ReviewSerializer, UserBookSerializer

User = get_user_model()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="domainuser",
        email="domainuser@example.com",
        password="password123",
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        username="otherdomainuser",
        email="otherdomainuser@example.com",
        password="password123",
    )


@pytest.fixture
def author(db):
    return Author.objects.create(name="Gabriel García Márquez")


@pytest.fixture
def sample_book(db, author):
    return Book.objects.create(
        title="Cien años de soledad",
        author=author,
        isbn="9780307474728",
    )


@pytest.fixture
def second_book(db, author):
    return Book.objects.create(
        title="El amor en los tiempos del cólera",
        author=author,
        isbn="9780307389732",
    )


@pytest.mark.django_db
class TestRatingDomainIntegrity:
    """Verifica que el rating esté estrictamente unificado en el rango 1 <= rating <= 5."""

    def test_review_valid_ratings(self, test_user, sample_book, second_book):
        r1 = Review.objects.create(user=test_user, book=sample_book, rating=1, title="Mínimo")
        assert r1.rating == 1

        r2 = Review.objects.create(user=test_user, book=second_book, rating=5, title="Máximo")
        assert r2.rating == 5

    def test_review_rating_model_validation_rejects_out_of_bounds(self, test_user, sample_book):
        # Validación a nivel de modelo full_clean()
        r_zero = Review(user=test_user, book=sample_book, rating=0)
        with pytest.raises(ValidationError):
            r_zero.full_clean()

        r_six = Review(user=test_user, book=sample_book, rating=6)
        with pytest.raises(ValidationError):
            r_six.full_clean()

        r_ten = Review(user=test_user, book=sample_book, rating=10)
        with pytest.raises(ValidationError):
            r_ten.full_clean()

    def test_review_database_check_constraint_rejects_out_of_bounds(self, test_user, sample_book):
        # Verificación directa de CheckConstraint en PostgreSQL
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=test_user, book=sample_book, rating=6)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=test_user, book=sample_book, rating=0)

    def test_userbook_valid_and_null_ratings(self, test_user, sample_book, second_book):
        ub1 = UserBook.objects.create(user=test_user, book=sample_book, rating=3)
        assert ub1.rating == 3

        ub2 = UserBook.objects.create(user=test_user, book=second_book, rating=None)
        assert ub2.rating is None

    def test_userbook_rating_model_validation_rejects_out_of_bounds(self, test_user, sample_book):
        ub_zero = UserBook(user=test_user, book=sample_book, rating=0)
        with pytest.raises(ValidationError):
            ub_zero.full_clean()

        ub_six = UserBook(user=test_user, book=sample_book, rating=6)
        with pytest.raises(ValidationError):
            ub_six.full_clean()

    def test_userbook_database_check_constraint_rejects_out_of_bounds(self, test_user, sample_book):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserBook.objects.create(user=test_user, book=sample_book, rating=8)

    def test_review_serializer_enforces_range(self, sample_book):
        s_valid = ReviewSerializer(data={'book_id': sample_book.id, 'rating': 4, 'title': 'Buena'})
        assert s_valid.is_valid(), s_valid.errors

        s_invalid_high = ReviewSerializer(data={'book_id': sample_book.id, 'rating': 6})
        assert not s_invalid_high.is_valid()
        assert 'rating' in s_invalid_high.errors

        s_invalid_zero = ReviewSerializer(data={'book_id': sample_book.id, 'rating': 0})
        assert not s_invalid_zero.is_valid()
        assert 'rating' in s_invalid_zero.errors

    def test_userbook_serializer_enforces_range(self, sample_book):
        s_valid = UserBookSerializer(data={'book_id': sample_book.id, 'rating': 5})
        assert s_valid.is_valid(), s_valid.errors

        s_invalid_ten = UserBookSerializer(data={'book_id': sample_book.id, 'rating': 10})
        assert not s_invalid_ten.is_valid()
        assert 'rating' in s_invalid_ten.errors

    def test_review_api_endpoint_rating_range(self, test_user, sample_book):
        client = APIClient()
        client.force_authenticate(user=test_user)

        # Rating válido 5 -> 201 Created
        resp = client.post('/api/v1/reviews/', {'book_id': sample_book.id, 'rating': 5, 'title': 'Excelente'})
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['rating'] == 5

        # Intento de rating 10 -> 400 Bad Request
        resp_bad = client.post('/api/v1/reviews/', {'book_id': sample_book.id, 'rating': 10})
        assert resp_bad.status_code == status.HTTP_400_BAD_REQUEST
        assert 'entre 1 y 5' in resp_bad.data['detail']


@pytest.mark.django_db
class TestDatabaseConstraintsAndIntegrity:
    """Verifica la solidez de las constraints relacionales de unicidad."""

    def test_userbook_unique_user_book(self, test_user, sample_book):
        UserBook.objects.create(user=test_user, book=sample_book)
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserBook.objects.create(user=test_user, book=sample_book)

    def test_review_unique_active_review_and_soft_delete_lifecycle(self, test_user, sample_book):
        # Primera reseña activa
        rev1 = Review.objects.create(user=test_user, book=sample_book, rating=4)

        # Intentar crear segunda reseña activa para el mismo libro y usuario debe fallar
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(user=test_user, book=sample_book, rating=5)

        # Al borrar la primera reseña por soft-delete, su deleted_at se rellena
        rev1.delete()
        assert rev1.deleted_at is not None
        assert not Review.objects.active().filter(id=rev1.id).exists()
        assert Review.objects.deleted().filter(id=rev1.id).exists()

        # Con la anterior eliminada, la constraint condicional permite registrar una nueva reseña activa
        rev2 = Review.objects.create(user=test_user, book=sample_book, rating=5)
        assert rev2.id != rev1.id
        assert Review.objects.active().filter(book=sample_book, user=test_user).count() == 1

    def test_review_like_unique_constraint(self, test_user, other_user, sample_book):
        review = Review.objects.create(user=other_user, book=sample_book, rating=5)
        ReviewLike.objects.create(user=test_user, review=review)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ReviewLike.objects.create(user=test_user, review=review)

    def test_reading_list_item_unique_constraint(self, test_user, sample_book):
        rlist = ReadingList.objects.create(user=test_user, name="Mis Favoritos")
        ReadingListItem.objects.create(reading_list=rlist, book=sample_book, position=1)

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                ReadingListItem.objects.create(reading_list=rlist, book=sample_book, position=2)

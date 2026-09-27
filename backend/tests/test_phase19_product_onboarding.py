import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingStatus, UserBook
from books.services.recommendation_service import _calculate_user_affinity

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def new_user(db):
    return User.objects.create_user(
        username="newreader",
        email="newreader@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def categories(db):
    c1 = Category.objects.create(name="Ciencia Ficción", slug="ciencia-ficcion")
    c2 = Category.objects.create(name="Fantasía Épica", slug="fantasia-epica")
    c3 = Category.objects.create(name="Novela Histórica", slug="novela-historica")
    return c1, c2, c3


@pytest.fixture
def sample_books(db, categories):
    c1, c2, c3 = categories
    author = Author.objects.create(name="Isaac Asimov")
    b1 = Book.objects.create(title="Fundación", author=author, average_rating=4.5)
    b1.categories.add(c1)

    b2 = Book.objects.create(title="El Hobbit", average_rating=4.8)
    b2.categories.add(c2)

    b3 = Book.objects.create(title="Yo, Robot", author=author, average_rating=4.2)
    b3.categories.add(c1)

    return b1, b2, b3


@pytest.mark.django_db
class TestPhase19ProductOnboarding:
    def test_onboarding_status_endpoint(self, api_client, new_user, sample_books, categories):
        api_client.force_authenticate(user=new_user)
        url = "/api/v1/users/onboarding/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["onboarding_completed"] is False
        assert isinstance(data["available_categories"], list)
        assert len(data["available_categories"]) >= 2
        assert isinstance(data["suggested_books"], list)
        assert len(data["suggested_books"]) >= 2

    def test_onboarding_complete_success(self, api_client, new_user, sample_books, categories):
        c1, c2, _ = categories
        b1, b2, _ = sample_books

        api_client.force_authenticate(user=new_user)
        url = "/api/v1/users/onboarding/"
        payload = {
            "category_ids": [c1.id, c2.id],
            "books": [
                {"book_id": b1.id, "status": "read", "rating": 5},
                {"book_id": b2.id, "status": "want_to_read"},
            ],
            "bio": "Lector apasionado de la ciencia ficción y la fantasía.",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True
        assert "first_recommendation" in response.data

        new_user.refresh_from_db()
        assert new_user.onboarding_completed is True
        assert new_user.bio == "Lector apasionado de la ciencia ficción y la fantasía."

        # Verificar categorías favoritas guardadas
        fav_ids = set(new_user.favorite_categories.values_list("id", flat=True))
        assert fav_ids == {c1.id, c2.id}

        # Verificar libros guardados en biblioteca
        ub1 = UserBook.objects.filter(user=new_user, book=b1).first()
        assert ub1 is not None
        assert ub1.status == ReadingStatus.READ
        assert ub1.is_read is True
        assert ub1.rating == 5

        ub2 = UserBook.objects.filter(user=new_user, book=b2).first()
        assert ub2 is not None
        assert ub2.status == ReadingStatus.WANT_TO_READ

    def test_onboarding_skip_endpoint(self, api_client, new_user):
        api_client.force_authenticate(user=new_user)
        url = "/api/v1/users/onboarding/skip/"
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] is True

        new_user.refresh_from_db()
        assert new_user.onboarding_completed is True

    def test_cold_start_recommendation_affinity(self, new_user, categories, sample_books):
        c1, _, _ = categories
        new_user.favorite_categories.add(c1)

        # Sin haber leído ningún libro, la afinidad debe reconocer su género favorito
        cat_aff, _, keywords = _calculate_user_affinity(new_user)
        assert c1.id in cat_aff
        assert cat_aff[c1.id] >= 1.0

    def test_user_profile_contains_onboarding_status(self, api_client, new_user):
        api_client.force_authenticate(user=new_user)
        url = "/api/v1/users/profile/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "onboarding_completed" in response.data
        assert response.data["onboarding_completed"] is False

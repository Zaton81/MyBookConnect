"""
Tests de verificación para la Fase 65 — Invalidación de Caché.
Prueban:
1. Cascada de invalidación reactiva ante nueva reseña:
   new review -> invalidate book rating & book cache -> invalidate recommendations -> invalidate trending -> invalidate user profile & stats.
2. Invalidación ante edición y borrado de reseñas.
3. Invalidación ante cambios de estado de lectura en UserBook.
4. Invalidación de perfil de usuario tras actualización y seguimiento.
5. Invalidación de libro y recomendaciones contextuales al modificar Book.
6. Invalidación de todos los periodos de tendencias ('week', 'month', 'year', 'all').
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from books.cache_utils import (
    book_detail_key,
    book_recommendations_key,
    invalidate_trending_cache,
    trending_key,
    user_profile_key,
    user_recommendations_key,
    user_stats_key,
)
from books.models import Author, Book, ReadingStatus, Review, UserBook

User = get_user_model()


@pytest.fixture
def user_alice(db):
    return User.objects.create_user(
        username="alice_c65",
        email="alice_c65@example.com",
        password="password123",
        bio="Lectora de novelas clásicas",
    )


@pytest.fixture
def user_bob(db):
    return User.objects.create_user(
        username="bob_c65",
        email="bob_c65@example.com",
        password="password123",
        bio="Lector de ciencia ficción",
    )


@pytest.fixture
def sample_book(db):
    author = Author.objects.create(name="Mario Vargas Llosa")
    return Book.objects.create(
        title="La ciudad y los perros",
        author=author,
        isbn="9788466333429",
    )


@pytest.mark.django_db(transaction=True)
class TestCacheInvalidationCascade:
    """Verifica la cascada reactiva explícita definida en el Roadmap."""

    def test_new_review_triggers_full_reactive_cascade(self, user_alice, sample_book):
        """
        Secuencia del Roadmap:
        new review -> invalidate book rating -> invalidate recommendations -> invalidate trending -> invalidate profile
        """
        # 1. Calentar cachés dependientes
        cache.set(book_detail_key(sample_book.id), {"title": sample_book.title}, timeout=600)
        cache.set(book_recommendations_key(sample_book.id), ["rec1", "rec2"], timeout=600)
        cache.set(f"similar_books_{sample_book.id}", ["sim1"], timeout=600)
        cache.set(user_recommendations_key(user_alice.id, "hybrid"), ["item1"], timeout=600)
        cache.set(user_recommendations_key(user_alice.id, "v3"), ["item_v3"], timeout=600)
        cache.set(f"user_pref_embedding_{user_alice.id}", [0.1, 0.2], timeout=600)
        cache.set(user_profile_key(user_alice.id), {"username": user_alice.username}, timeout=600)
        cache.set(user_stats_key(user_alice.id), {"total_books": 5}, timeout=600)

        for p in ("week", "month", "year", "all"):
            cache.set(trending_key(p), [sample_book.id], timeout=600)

        # 2. Crear reseña vía API
        client = APIClient()
        client.force_authenticate(user=user_alice)
        resp = client.post(
            "/api/v1/reviews/",
            {"book_id": sample_book.id, "rating": 5, "title": "Impactante", "text": "Una obra imprescindible."},
            format="json",
        )
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

        # 3. Comprobar que la cascada invalidó TODOS los componentes dependientes
        assert cache.get(book_detail_key(sample_book.id)) is None, "book_cache no invalidada"
        assert cache.get(book_recommendations_key(sample_book.id)) is None, "book_recommendations_cache no invalidada"
        assert cache.get(f"similar_books_{sample_book.id}") is None, "similar_books no invalidado"
        assert cache.get(user_recommendations_key(user_alice.id, "hybrid")) is None, "user_recommendations_cache no invalidada"
        assert cache.get(user_recommendations_key(user_alice.id, "v3")) is None, "user_recommendations_v3 no invalidada"
        assert cache.get(f"user_pref_embedding_{user_alice.id}") is None, "user_pref_embedding no invalidado"
        assert cache.get(user_profile_key(user_alice.id)) is None, "profile_cache no invalidada"
        assert cache.get(user_stats_key(user_alice.id)) is None, "stats_cache no invalidada"

        for p in ("week", "month", "year", "all"):
            assert cache.get(trending_key(p)) is None, f"trending_cache ({p}) no invalidada"

    def test_review_update_and_delete_invalidation(self, user_alice, sample_book):
        """Editar o eliminar una reseña debe invalidar book cache, trending y perfil."""
        review = Review.objects.create(user=user_alice, book=sample_book, rating=4, text="Buena")

        # Calentar cachés
        cache.set(book_detail_key(sample_book.id), {"title": sample_book.title}, timeout=600)
        cache.set(trending_key("week"), ["dummy"], timeout=600)
        cache.set(user_profile_key(user_alice.id), {"user": "data"}, timeout=600)

        # Modificar reseña
        review.rating = 5
        review.save(update_fields=["rating"])

        assert cache.get(book_detail_key(sample_book.id)) is None
        assert cache.get(trending_key("week")) is None
        assert cache.get(user_profile_key(user_alice.id)) is None

        # Calentar de nuevo y borrar
        cache.set(book_detail_key(sample_book.id), {"title": sample_book.title}, timeout=600)
        review.delete()
        assert cache.get(book_detail_key(sample_book.id)) is None


@pytest.mark.django_db(transaction=True)
class TestUserBookAndProfileCacheInvalidation:
    """Verifica la invalidación de perfiles y recomendaciones ante actividad de lectura y red social."""

    def test_userbook_status_change_invalidates_caches(self, user_alice, sample_book):
        cache.set(user_profile_key(user_alice.id), {"id": user_alice.id}, timeout=600)
        cache.set(user_stats_key(user_alice.id), {"books_read": 2}, timeout=600)
        cache.set(user_recommendations_key(user_alice.id, "hybrid"), ["rec"], timeout=600)
        cache.set(trending_key("month"), ["trend"], timeout=600)

        # Crear UserBook a estado 'reading'
        ub = UserBook.objects.create(
            user=user_alice,
            book=sample_book,
            status=ReadingStatus.READING,
            progress=50,
        )

        assert cache.get(user_profile_key(user_alice.id)) is None
        assert cache.get(user_stats_key(user_alice.id)) is None
        assert cache.get(user_recommendations_key(user_alice.id, "hybrid")) is None
        assert cache.get(trending_key("month")) is None

        # Calentar y actualizar a 'read'
        cache.set(user_profile_key(user_alice.id), {"id": user_alice.id}, timeout=600)
        ub.status = ReadingStatus.READ
        ub.save()
        assert cache.get(user_profile_key(user_alice.id)) is None

    def test_user_profile_view_caches_and_invalidates_on_update(self, user_alice):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        # 1. Primera consulta: puebla caché
        resp1 = client.get("/api/v1/auth/profile/")
        assert resp1.status_code == status.HTTP_200_OK
        cache_key = user_profile_key(user_alice.id)
        assert cache.get(cache_key) is not None
        assert cache.get(cache_key)["username"] == user_alice.username

        # 2. Segunda consulta: hit de caché
        resp2 = client.get("/api/v1/auth/profile/")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["username"] == user_alice.username

        # 3. Actualizar perfil -> debe invalidar la caché
        resp_update = client.patch("/api/v1/auth/profile/update/", {"bio": "Biografía actualizada"}, format="json")
        assert resp_update.status_code == status.HTTP_200_OK
        assert cache.get(cache_key) is None

    def test_follow_and_unfollow_invalidates_profiles_and_recommendations(self, user_alice, user_bob):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        # Calentar cachés de ambos usuarios
        cache.set(user_profile_key(user_alice.id), {"username": "alice"}, timeout=600)
        cache.set(user_profile_key(user_bob.id), {"username": "bob"}, timeout=600)
        cache.set(user_recommendations_key(user_alice.id, "social"), ["rec_social"], timeout=600)

        # Follow
        r1 = client.post(f"/api/v1/users/{user_bob.id}/follow/")
        assert r1.status_code == status.HTTP_200_OK
        assert cache.get(user_profile_key(user_alice.id)) is None
        assert cache.get(user_profile_key(user_bob.id)) is None
        assert cache.get(user_recommendations_key(user_alice.id, "social")) is None

        # Calentar y unfollow
        cache.set(user_profile_key(user_alice.id), {"username": "alice"}, timeout=600)
        cache.set(user_profile_key(user_bob.id), {"username": "bob"}, timeout=600)

        r2 = client.post(f"/api/v1/users/{user_bob.id}/unfollow/")
        assert r2.status_code == status.HTTP_200_OK
        assert cache.get(user_profile_key(user_alice.id)) is None
        assert cache.get(user_profile_key(user_bob.id)) is None


@pytest.mark.django_db(transaction=True)
class TestBookAndTrendingDirectInvalidation:
    """Verifica las funciones directas de invalidación de tendencias y libros."""

    def test_invalidate_trending_cache_clears_all_periods(self):
        for p in ("week", "month", "year", "all"):
            cache.set(trending_key(p), [1, 2, 3], timeout=600)

        invalidate_trending_cache()

        for p in ("week", "month", "year", "all"):
            assert cache.get(trending_key(p)) is None

    def test_book_update_signal_invalidates_caches(self, sample_book):
        cache.set(book_detail_key(sample_book.id), {"title": sample_book.title}, timeout=600)
        cache.set(book_recommendations_key(sample_book.id), ["rec"], timeout=600)
        cache.set(trending_key("week"), ["trend"], timeout=600)

        sample_book.title = "La ciudad y los perros (Edición Conmemorativa)"
        sample_book.save(update_fields=["title"])

        assert cache.get(book_detail_key(sample_book.id)) is None
        assert cache.get(book_recommendations_key(sample_book.id)) is None
        assert cache.get(trending_key("week")) is None

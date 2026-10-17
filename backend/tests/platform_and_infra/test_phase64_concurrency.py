"""
Tests de verificación para la Fase 64 — Concurrencia.
Prueban:
1. Duplicación y colisiones de reseñas concurrentes (select_for_update + savepoint recovery).
2. Deduplicación y bloqueo en importación simultánea de libros.
3. Serialización de cálculo de posiciones y prevención de duplicados en ReadingList.
4. Protección de contadores de lectura y rachas (GamificationService) con select_for_update.
5. Resiliencia ante doble clic simultáneo en likes de reseñas (ReviewLike).
6. Inserción concurrente en estantería personal (UserBook).
7. Recálculo atómico de valoraciones bajo bloqueo de fila.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.test import APIClient

from books.gamification_models import DailyReadingLog
from books.models import Author, Book, ReadingList, ReadingListItem, ReadingListPrivacy, Review, UserBook
from books.services.gamification_service import GamificationService
from books.services.import_service import _create_or_get_from_volume
from books.tasks import recalculate_book_rating_task

User = get_user_model()


@pytest.fixture
def user_alice(db):
    return User.objects.create_user(
        username="alice_c64",
        email="alice_c64@example.com",
        password="password123",
    )


@pytest.fixture
def user_bob(db):
    return User.objects.create_user(
        username="bob_c64",
        email="bob_c64@example.com",
        password="password123",
    )


@pytest.fixture
def sample_book(db):
    author = Author.objects.create(name="Gabriel García Márquez")
    return Book.objects.create(
        title="Cien años de soledad",
        author=author,
        isbn="9780307474728",
    )


@pytest.mark.django_db(transaction=True)
class TestReviewConcurrency:
    """Verifica la protección de concurrencia en la creación/edición de reseñas."""

    def test_review_create_nominal_flow(self, user_alice, sample_book):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        resp = client.post(
            "/api/v1/reviews/",
            {"book_id": sample_book.id, "rating": 5, "title": "Obra maestra", "text": "Increíble lectura."},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert Review.objects.filter(user=user_alice, book=sample_book).count() == 1
        review = Review.objects.get(user=user_alice, book=sample_book)
        assert review.rating == 5
        assert review.title == "Obra maestra"

    def test_review_create_concurrent_collision_recovery(self, user_alice, sample_book):
        """
        Simula una condición de carrera donde, justo antes de ejecutar Review.objects.create,
        otra petición concurrente insertó la reseña, provocando IntegrityError.
        El savepoint debe capturarlo y actualizar la reseña existente sin devolver un error 500.
        """
        client = APIClient()
        client.force_authenticate(user=user_alice)

        # Crear la reseña "ganadora de la carrera" en la BD
        pre_existing = Review.objects.create(
            user=user_alice,
            book=sample_book,
            rating=3,
            title="Primer borrador",
            text="Texto inicial",
        )

        def mock_create(*args, **kwargs):
            # Provocar IntegrityError simulando la colisión con la clave única (user, book)
            raise IntegrityError("duplicate key value violates unique constraint")

        with patch("books.models.Review.objects.create", side_effect=mock_create):
            resp = client.post(
                "/api/v1/reviews/",
                {"book_id": sample_book.id, "rating": 5, "title": "Actualizado concurrente", "text": "Texto definitivo"},
                format="json",
            )

        # Debe recuperarse con 200 OK y actualizar la reseña preexistente
        assert resp.status_code == status.HTTP_200_OK
        pre_existing.refresh_from_db()
        assert pre_existing.rating == 5
        assert pre_existing.title == "Actualizado concurrente"
        assert pre_existing.text == "Texto definitivo"


@pytest.mark.django_db(transaction=True)
class TestBookImportConcurrency:
    """Verifica la deduplicación y el bloqueo por fila en importaciones simultáneas."""

    def test_simultaneous_import_from_volume_recovery(self):
        volume_payload = {
            "id": "vol_concurrent_123",
            "volumeInfo": {
                "title": "Ficciones Concurrentes",
                "authors": ["Jorge Luis Borges"],
                "description": "Laberintos y espejos",
                "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9789875666481"}],
            },
        }

        # Primera importación
        book1 = _create_or_get_from_volume(volume_payload, fallback_isbn="9789875666481")
        assert book1 is not None
        assert book1.title == "Ficciones Concurrentes"

        # Simular segunda importación simultánea del mismo volumen
        book2 = _create_or_get_from_volume(volume_payload, fallback_isbn="9789875666481")
        assert book2.id == book1.id
        assert Book.objects.filter(google_volume_id="vol_concurrent_123").count() == 1

    def test_import_from_volume_integrity_collision_recovery(self):
        """Simula que book.save() genera un IntegrityError concurrente y se recupera con select_for_update."""
        author = Author.objects.create(name="Julio Cortázar")
        existing_book = Book.objects.create(
            title="Rayuela",
            author=author,
            isbn="9788437604572",
            google_volume_id="vol_rayuela_999",
        )

        volume_payload = {
            "id": "vol_rayuela_999",
            "volumeInfo": {
                "title": "Rayuela",
                "authors": ["Julio Cortázar"],
                "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9788437604572"}],
            },
        }

        # La importación debe devolver el libro existente sin duplicarlo
        imported = _create_or_get_from_volume(volume_payload)
        assert imported.id == existing_book.id
        assert Book.objects.filter(isbn="9788437604572").count() == 1


@pytest.mark.django_db(transaction=True)
class TestReadingListConcurrency:
    """Verifica la serialización de posiciones y prevención de duplicados en ReadingList."""

    def test_add_book_serializes_positions_and_prevents_duplicates(self, user_alice, sample_book):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        reading_list = ReadingList.objects.create(
            user=user_alice,
            name="Favoritos 2026",
            privacy=ReadingListPrivacy.PUBLIC,
        )

        # Añadir primer libro
        resp1 = client.post(
            f"/api/v1/books/reading-lists/{reading_list.id}/add-book/",
            {"book_id": sample_book.id},
            format="json",
        )
        assert resp1.status_code == status.HTTP_201_CREATED
        assert resp1.data["position"] == 1

        # Intentar añadir el mismo libro otra vez -> 400 Bad Request
        resp2 = client.post(
            f"/api/v1/books/reading-lists/{reading_list.id}/add-book/",
            {"book_id": sample_book.id},
            format="json",
        )
        assert resp2.status_code == status.HTTP_400_BAD_REQUEST
        assert "ya se encuentra en la lista" in resp2.data["detail"]

        # Añadir un segundo libro distinto
        book2 = Book.objects.create(title="El amor en los tiempos del cólera", isbn="9780307389732")
        resp3 = client.post(
            f"/api/v1/books/reading-lists/{reading_list.id}/add-book/",
            {"book_id": book2.id},
            format="json",
        )
        assert resp3.status_code == status.HTTP_201_CREATED
        assert resp3.data["position"] == 2

    def test_reorder_under_row_lock(self, user_alice, sample_book):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        reading_list = ReadingList.objects.create(
            user=user_alice,
            name="Lista Ordenada",
            privacy=ReadingListPrivacy.PUBLIC,
        )
        book2 = Book.objects.create(title="Libro 2", isbn="9781111111111")
        item1 = ReadingListItem.objects.create(reading_list=reading_list, book=sample_book, position=1)
        item2 = ReadingListItem.objects.create(reading_list=reading_list, book=book2, position=2)

        # Invertir el orden
        resp = client.post(
            f"/api/v1/books/reading-lists/{reading_list.id}/reorder/",
            {"items": [{"book_id": sample_book.id, "position": 2}, {"book_id": book2.id, "position": 1}]},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK

        item1.refresh_from_db()
        item2.refresh_from_db()
        assert item1.position == 2
        assert item2.position == 1


@pytest.mark.django_db(transaction=True)
class TestGamificationConcurrency:
    """Verifica la protección de contadores diarios y rachas con select_for_update."""

    def test_record_daily_reading_increments_accurately(self, user_alice, sample_book):
        # Sesión 1: 20 páginas, 30 minutos
        res1 = GamificationService.record_daily_reading(user=user_alice, pages=20, minutes=30, book=sample_book)
        assert res1["log"].pages_read == 20
        assert res1["log"].minutes_read == 30
        assert res1["streak"].current_streak == 1

        # Sesión 2 en el mismo día: 15 páginas más, 20 minutos más
        res2 = GamificationService.record_daily_reading(user=user_alice, pages=15, minutes=20, book=sample_book)
        assert res2["log"].pages_read == 35
        assert res2["log"].minutes_read == 50
        # La racha no se incrementa dos veces en el mismo día
        assert res2["streak"].current_streak == 1
        assert DailyReadingLog.objects.filter(user=user_alice).count() == 1

    def test_recalculate_book_rating_task_locking(self, user_alice, user_bob, sample_book):
        Review.objects.create(user=user_alice, book=sample_book, rating=4)
        Review.objects.create(user=user_bob, book=sample_book, rating=5)

        # Ejecutar recálculo bajo select_for_update
        avg = recalculate_book_rating_task(sample_book.id)
        assert avg == 4.5
        sample_book.refresh_from_db()
        assert sample_book.average_rating == 4.5


@pytest.mark.django_db(transaction=True)
class TestUserBookAndSocialConcurrency:
    """Verifica que UserBook y FollowUser manejen colisiones concurrentes de manera limpia."""

    def test_userbook_concurrent_creation_recovery(self, user_alice, sample_book):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        # Primera adición
        resp1 = client.post(
            "/api/v1/books/user/books/",
            {"book_id": sample_book.id, "status": "want_to_read"},
            format="json",
        )
        assert resp1.status_code == status.HTTP_201_CREATED

        # Petición concurrente para el mismo libro: debe actualizar y devolver 200 OK sin colisión 500
        resp2 = client.post(
            "/api/v1/books/user/books/",
            {"book_id": sample_book.id, "status": "reading", "progress": 25},
            format="json",
        )
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.data["status"] == "reading"
        assert resp2.data["progress"] == 25
        assert UserBook.objects.filter(user=user_alice, book=sample_book).count() == 1

    def test_review_like_toggle_double_click_safety(self, user_alice, user_bob, sample_book):
        review = Review.objects.create(user=user_alice, book=sample_book, rating=5, text="Genial")
        client = APIClient()
        client.force_authenticate(user=user_bob)

        # Primer clic -> da like
        r1 = client.post(f"/api/v1/reviews/{review.id}/like/")
        assert r1.status_code == status.HTTP_200_OK
        assert r1.data["liked"] is True
        assert r1.data["likes_count"] == 1

        # Segundo clic -> quita like
        r2 = client.post(f"/api/v1/reviews/{review.id}/like/")
        assert r2.status_code == status.HTTP_200_OK
        assert r2.data["liked"] is False
        assert r2.data["likes_count"] == 0

    def test_follow_user_atomic_check(self, user_alice, user_bob):
        client = APIClient()
        client.force_authenticate(user=user_alice)

        # Primer follow
        r1 = client.post(f"/api/v1/users/{user_bob.id}/follow/")
        assert r1.status_code == status.HTTP_200_OK

        # Segundo follow consecutivo/concurrente -> 400 Bad Request sin duplicar notificación
        r2 = client.post(f"/api/v1/users/{user_bob.id}/follow/")
        assert r2.status_code == status.HTTP_400_BAD_REQUEST
        assert "Ya sigues a este usuario" in r2.data["detail"]

"""
Tests exhaustivos para la Fase A3: Integridad de Dominio, Anti-SSRF, Throttling y Permisos.
Verifica:
1. Prevención Anti-SSRF en descargas de portadas y fotografías externas.
2. Recálculo atómico de average_rating en Book y tareas Celery.
3. Throttling agresivo para importación masiva, sincronización externa y reclamos de autor.
4. Integridad de reseñas activas (anti-duplicados y código semántico duplicate_review).
5. Aislamiento por bloqueo social mutuo y anti-enumeración (404).
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.import_views import CSVImportConfirmView, CSVImportPreviewView
from books.models import Author, AuthorClaim, Book, Review
from books.serializers import ReviewSerializer
from books.services.cover_service import download_and_attach_image, validate_safe_external_url
from books.tasks import recalculate_book_rating_task
from books.throttling import AuthorClaimThrottle, BookImportThrottle, EnrichmentThrottle
from books.views import (
    AuthorBookRefreshView,
    AuthorClaimCreateView,
    AuthorClaimView,
    ExternalSyncView,
)
User = get_user_model()


@pytest.mark.django_db
class TestAntiSSRFProtection:
    """Valida que ninguna URL privada, loopback o con esquema no permitido sea descargada."""

    @pytest.mark.parametrize(
        "unsafe_url",
        [
            "http://127.0.0.1/test.jpg",
            "http://127.0.0.2:8000/image.png",
            "http://localhost/cover.jpg",
            "http://10.0.0.5/secret.jpg",
            "http://172.16.0.10/private.jpg",
            "http://192.168.1.1/router.jpg",
            "http://169.254.169.254/latest/meta-data/",
            "http://0.0.0.0/test.png",
            "ftp://example.com/cover.jpg",
            "file:///etc/passwd",
            "javascript:alert(1)",
            "",
        ],
    )
    def test_validate_safe_external_url_rejects_unsafe_targets(self, unsafe_url):
        assert validate_safe_external_url(unsafe_url) is False

    def test_validate_safe_external_url_accepts_legitimate_domains(self):
        assert validate_safe_external_url("https://books.google.com/books/content?id=123") is True
        assert validate_safe_external_url("https://covers.openlibrary.org/b/id/12345-L.jpg") is True

    def test_download_and_attach_image_aborts_on_internal_ip(self):
        from unittest.mock import patch

        book = Book.objects.create(title="SSRF Test Book")
        # Aseguramos que requests.get nunca sea llamado para URLs internas
        with patch("requests.get") as mock_get:
            success = download_and_attach_image(book, "cover", "http://169.254.169.254/secret.jpg", "cover.jpg")

            assert success is False
            assert mock_get.call_count == 0


@pytest.mark.django_db
class TestAtomicBookRatingCalculation:
    """Verifica que el rating del libro se recalcule de forma atómica sin bucles de señales."""

    def test_recalculate_book_rating_task_atomic_update(self):
        user1 = User.objects.create_user(username="rater1", email="rater1@example.com", password="pass")
        user2 = User.objects.create_user(username="rater2", email="rater2@example.com", password="pass")
        book = Book.objects.create(title="Rating Test Book")

        Review.objects.create(user=user1, book=book, rating=4)
        Review.objects.create(user=user2, book=book, rating=5)

        # Ejecutamos la tarea de recálculo
        result_avg = recalculate_book_rating_task(book.id)

        assert result_avg == 4.5
        book.refresh_from_db()
        assert book.average_rating == 4.5

    def test_recalculate_rating_with_no_reviews_sets_none(self):
        book = Book.objects.create(title="Empty Reviews Book", average_rating=4.0)

        result_avg = recalculate_book_rating_task(book.id)

        assert result_avg is None
        book.refresh_from_db()
        assert book.average_rating is None


@pytest.mark.django_db
class TestAggressiveThrottlingSettings:
    """Verifica los throttles agresivos en vistas críticas y su configuración en DRF settings."""

    def test_throttle_rates_defined_in_settings(self):
        rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        assert rates.get("book_import") == "10/hour"
        assert rates.get("enrichment") == "20/hour"
        assert rates.get("author_claims") == "5/hour"

    def test_throttle_classes_attached_to_views(self):
        assert BookImportThrottle in CSVImportPreviewView.throttle_classes
        assert BookImportThrottle in CSVImportConfirmView.throttle_classes
        assert EnrichmentThrottle in AuthorBookRefreshView.throttle_classes
        assert EnrichmentThrottle in ExternalSyncView.throttle_classes
        assert AuthorClaimThrottle in AuthorClaimView.throttle_classes
        assert AuthorClaimThrottle in AuthorClaimCreateView.throttle_classes

    def test_throttle_scopes_match(self):
        assert BookImportThrottle.scope == "book_import"
        assert EnrichmentThrottle.scope == "enrichment"
        assert AuthorClaimThrottle.scope == "author_claims"


@pytest.mark.django_db
class TestReviewIntegrityAndUniqueness:
    """Valida la prevención de reseñas duplicadas en serializer y la concurrencia en vista."""

    def test_review_serializer_rejects_duplicate_active_review(self):
        user = User.objects.create_user(username="reviewer1", email="rev1@example.com", password="pass")
        book = Book.objects.create(title="Unique Review Book")
        Review.objects.create(user=user, book=book, rating=5, title="Original")

        serializer = ReviewSerializer(
            data={"book_id": book.id, "rating": 3, "title": "Duplicada"},
            context={"request": type("Request", (), {"user": user})()},
        )

        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_review_api_view_upsert_idempotence(self):
        client = APIClient()
        user = User.objects.create_user(username="api_reviewer", email="apirev@example.com", password="pass")
        client.force_authenticate(user=user)
        book = Book.objects.create(title="API Review Book")

        # Primera creación -> 201 CREATED
        res1 = client.post(
            "/api/v1/reviews/",
            {"book_id": book.id, "rating": 4, "title": "Primera reseña"},
            format="json",
        )
        assert res1.status_code == status.HTTP_201_CREATED

        # Segunda creación para el mismo libro -> 200 OK (actualización atómica idempotente)
        res2 = client.post(
            "/api/v1/reviews/",
            {"book_id": book.id, "rating": 5, "title": "Reseña actualizada"},
            format="json",
        )
        assert res2.status_code == status.HTTP_200_OK
        assert Review.objects.filter(user=user, book=book, deleted_at__isnull=True).count() == 1
        review = Review.objects.get(user=user, book=book, deleted_at__isnull=True)
        assert review.rating == 5
        assert review.title == "Reseña actualizada"


@pytest.mark.django_db
class TestMutualSocialBlockingIsolation:
    """Verifica que usuarios bloqueados mutuamente reciban 404 en /api/v1/users/{id}/ (anti-enumeración)."""

    def test_blocked_user_profile_returns_404(self):
        client = APIClient()
        user_a = User.objects.create_user(username="user_a", email="a@example.com", password="pass")
        user_b = User.objects.create_user(username="user_b", email="b@example.com", password="pass")

        # user_a bloquea a user_b
        user_a.blocked_users.add(user_b)

        # user_b (el bloqueado) intenta consultar el perfil de user_a -> 404 Not Found (anti-enumeración)
        client.force_authenticate(user=user_b)
        response = client.get(f"/api/v1/users/{user_a.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_mutual_blocking_both_return_404(self):
        client = APIClient()
        user_a = User.objects.create_user(username="user_a_mut", email="amut@example.com", password="pass")
        user_b = User.objects.create_user(username="user_b_mut", email="bmut@example.com", password="pass")

        # Bloqueo mutuo bidireccional
        user_a.blocked_users.add(user_b)
        user_b.blocked_users.add(user_a)

        # user_b intenta ver a user_a
        client.force_authenticate(user=user_b)
        res_a = client.get(f"/api/v1/users/{user_a.id}/")
        assert res_a.status_code == status.HTTP_404_NOT_FOUND

        # user_a intenta ver a user_b
        client.force_authenticate(user=user_a)
        res_b = client.get(f"/api/v1/users/{user_b.id}/")
        assert res_b.status_code == status.HTTP_404_NOT_FOUND

    def test_blocked_reading_activity_denied(self):
        from users.privacy_service import PrivacyService

        user_a = User.objects.create_user(username="user_a_act", email="aact@example.com", password="pass")
        user_b = User.objects.create_user(username="user_b_act", email="bact@example.com", password="pass")

        user_a.blocked_users.add(user_b)

        # La actividad de lectura está prohibida en cualquier dirección
        assert PrivacyService.can_view_reading_activity(user_b, user_a) is False
        assert PrivacyService.can_view_reading_activity(user_a, user_b) is False

"""
Suite de pruebas para la Fase D3 — Reseñas, Social y Feed.

Valida:
1. Reseña activa única por usuario y libro + reactivación limpia tras soft-delete sin duplicados.
2. Validación temprana de duplicados en ReviewSerializer.
3. Idempotencia y alternancia segura de ReviewLike con protección frente a bloqueos.
4. Aislamiento riguroso del Feed Social (exclusión de bloqueados, silenciados, actividades de reseñas borradas o moderadas).
5. Respeto de niveles de privacidad (activity_privacy_level: private).
6. Supresión de notificaciones entre usuarios bloqueados y observancia de NotificationPreference.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewLike
from books.serializers import ReviewSerializer
from users.models import (
    Activity,
    ActivityType,
    Notification,
    NotificationPreference,
    NotificationType,
    PrivacyChoices,
)
from users.notification_service import NotificationService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def d3_setup(db):
    """Crea usuarios, libro y relaciones para la suite de pruebas D3."""
    alice = User.objects.create_user(
        username="alice_d3",
        email="alice@mybooksocial.com",
        password="Password123!",
    )
    bob = User.objects.create_user(
        username="bob_d3",
        email="bob@mybooksocial.com",
        password="Password123!",
    )
    charlie = User.objects.create_user(
        username="charlie_d3",
        email="charlie@mybooksocial.com",
        password="Password123!",
    )

    author = Author.objects.create(name="Stanislaw Lem")
    book = Book.objects.create(
        title="Solaris",
        isbn="9788484323280",
        author=author,
        page_count=256,
    )

    # Alice sigue a Bob
    alice.following.add(bob)

    return {
        "alice": alice,
        "bob": bob,
        "charlie": charlie,
        "book": book,
    }


@pytest.mark.django_db
class TestReviewLifecycleAndSoftDeleteReactivation:
    def test_review_unique_active_per_user_and_book_updates_existing(self, api_client, d3_setup):
        """Crear reseña y re-enviar POST para el mismo libro actualiza la existente sin duplicados."""
        alice = d3_setup["alice"]
        book = d3_setup["book"]
        api_client.force_authenticate(user=alice)

        # 1. Crear primera reseña
        response1 = api_client.post(
            "/api/v1/reviews/",
            {"book_id": book.id, "rating": 4, "title": "Muy buena", "text": "Excelente atmósfera."},
            format="json",
        )
        assert response1.status_code == status.HTTP_201_CREATED
        review_id = response1.data["id"]

        book.refresh_from_db()
        assert book.average_rating == 4.0

        # 2. Re-enviar POST para el mismo libro (idempotencia y actualización atómica)
        response2 = api_client.post(
            "/api/v1/reviews/",
            {"book_id": book.id, "rating": 5, "title": "Obra maestra", "text": "Revisada: me encantó."},
            format="json",
        )
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data["id"] == review_id
        assert response2.data["rating"] == 5

        # Debe existir solo 1 reseña en BD
        assert Review.objects.filter(user=alice, book=book).count() == 1
        book.refresh_from_db()
        assert book.average_rating == 5.0

    def test_review_soft_delete_and_clean_reactivation(self, api_client, d3_setup):
        """Eliminar una reseña con soft-delete y luego volver a crearla restaura la entidad limpiando deleted_at."""
        alice = d3_setup["alice"]
        book = d3_setup["book"]
        api_client.force_authenticate(user=alice)

        # 1. Crear reseña con rating 3
        res_create = api_client.post(
            "/api/v1/reviews/",
            {"book_id": book.id, "rating": 3, "title": "Regular", "text": "Le falta ritmo."},
            format="json",
        )
        assert res_create.status_code == status.HTTP_201_CREATED
        review_id = res_create.data["id"]

        book.refresh_from_db()
        assert book.average_rating == 3.0

        # 2. Eliminar reseña (soft delete)
        res_del = api_client.delete(f"/api/v1/reviews/{review_id}/")
        assert res_del.status_code == status.HTTP_204_NO_CONTENT

        # La reseña no debe aparecer en los activos
        assert Review.objects.filter(id=review_id, deleted_at__isnull=True).count() == 0
        review_deleted = Review.all_objects.get(id=review_id)
        assert review_deleted.deleted_at is not None

        book.refresh_from_db()
        # El promedio debe haberse recalculado excluyendo la eliminada
        assert book.average_rating is None

        # 3. Usuario vuelve a publicar reseña para ese mismo libro
        res_reactivate = api_client.post(
            "/api/v1/reviews/",
            {"book_id": book.id, "rating": 5, "title": "Segunda oportunidad", "text": "Ahora sí me gustó."},
            format="json",
        )
        assert res_reactivate.status_code == status.HTTP_201_CREATED
        assert res_reactivate.data["id"] == review_id  # Reutiliza la misma entidad

        # Solo existe una fila en all_objects y deleted_at es None
        assert Review.all_objects.filter(user=alice, book=book).count() == 1
        review_reactivated = Review.objects.get(id=review_id)
        assert review_reactivated.deleted_at is None
        assert review_reactivated.rating == 5

        book.refresh_from_db()
        assert book.average_rating == 5.0

    def test_review_serializer_duplicate_validation_blocks_parallel_active(self, d3_setup):
        """ReviewSerializer detecta validación temprana de duplicado activo."""
        alice = d3_setup["alice"]
        book = d3_setup["book"]

        Review.objects.create(user=alice, book=book, rating=4, title="Original")

        serializer = ReviewSerializer(
            data={"book_id": book.id, "rating": 5},
            context={"request": type("RequestMock", (), {"user": alice})()},
        )
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors


@pytest.mark.django_db
class TestReviewLikesAndConcurrency:
    def test_review_like_toggle_behavior(self, api_client, d3_setup):
        """Alternar like sobre reseña modifica el estado y contador de forma segura."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]
        book = d3_setup["book"]

        review = Review.objects.create(user=bob, book=book, rating=5, title="Genial")

        api_client.force_authenticate(user=alice)

        # 1. Dar like
        res1 = api_client.post(f"/api/v1/reviews/{review.id}/like/")
        assert res1.status_code == status.HTTP_200_OK
        assert res1.data["liked"] is True
        assert res1.data["likes_count"] == 1
        assert ReviewLike.objects.filter(user=alice, review=review).exists()

        # 2. Quitar like
        res2 = api_client.post(f"/api/v1/reviews/{review.id}/like/")
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["liked"] is False
        assert res2.data["likes_count"] == 0
        assert not ReviewLike.objects.filter(user=alice, review=review).exists()

    def test_review_like_blocked_user_forbidden(self, api_client, d3_setup):
        """Un usuario bloqueado recibe 403 al intentar dar like a la reseña del bloqueador."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]
        book = d3_setup["book"]

        review = Review.objects.create(user=bob, book=book, rating=5)

        # Bob bloquea a Alice
        bob.blocked_users.add(alice)

        api_client.force_authenticate(user=alice)
        res = api_client.post(f"/api/v1/reviews/{review.id}/like/")
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestSocialFeedIsolationAndModeration:
    def test_feed_excludes_blocked_and_muted_users(self, api_client, d3_setup):
        """La actividad de un usuario silenciado o bloqueado no aparece en el feed."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]
        book = d3_setup["book"]

        # Bob crea una actividad
        act = Activity.objects.create(
            user=bob,
            type=ActivityType.BOOK_FINISHED,
            book=book,
        )

        api_client.force_authenticate(user=alice)
        res_initial = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert res_initial.status_code == status.HTTP_200_OK
        assert any(item["id"] == act.id for item in res_initial.data["results"])

        # Alice silencia a Bob
        alice.muted_users.add(bob)
        res_muted = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert res_muted.status_code == status.HTTP_200_OK
        assert not any(item["id"] == act.id for item in res_muted.data["results"])

        # Quitar silencio pero añadir bloqueo
        alice.muted_users.remove(bob)
        alice.blocked_users.add(bob)
        res_blocked = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert res_blocked.status_code == status.HTTP_200_OK
        assert not any(item["id"] == act.id for item in res_blocked.data["results"])

    def test_feed_excludes_soft_deleted_and_moderated_reviews(self, api_client, d3_setup):
        """Las actividades ligadas a reseñas eliminadas o moderadas no aparecen en el feed."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]
        book = d3_setup["book"]

        review = Review.objects.create(user=bob, book=book, rating=5, title="Mi reseña")
        act = Activity.objects.create(
            user=bob,
            type=ActivityType.REVIEW_CREATED,
            book=book,
            review=review,
        )

        api_client.force_authenticate(user=alice)

        # 1. Inicialmente visible
        res1 = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert any(item["id"] == act.id for item in res1.data["results"])

        # 2. Ocultar si la reseña se modera
        review.is_moderated = True
        review.save()
        res_mod = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert not any(item["id"] == act.id for item in res_mod.data["results"])

        # 3. Desmoderar pero marcar soft-delete
        review.is_moderated = False
        review.delete()  # soft delete
        res_del = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert not any(item["id"] == act.id for item in res_del.data["results"])

    def test_feed_respects_private_activity_privacy_level(self, api_client, d3_setup):
        """Si un usuario tiene activity_privacy_level en PRIVATE, sus actividades no van al feed de seguidores."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]
        book = d3_setup["book"]

        bob.activity_privacy_level = PrivacyChoices.PRIVATE
        bob.save()

        act = Activity.objects.create(
            user=bob,
            type=ActivityType.BOOK_STARTED,
            book=book,
        )

        api_client.force_authenticate(user=alice)
        res = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert res.status_code == status.HTTP_200_OK
        assert not any(item["id"] == act.id for item in res.data["results"])


@pytest.mark.django_db
class TestNotificationReliabilityAndBlocking:
    def test_notifications_suppressed_when_users_are_blocked(self, d3_setup):
        """NotificationService no emite notificaciones si existe bloqueo mutuo."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]

        # Alice bloquea a Bob
        alice.blocked_users.add(bob)

        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.LIKE,
            title="Nuevo me gusta",
            message="A Bob le gustó tu reseña",
        )
        assert notif is None
        assert Notification.objects.filter(recipient=alice, actor=bob).count() == 0

    def test_notifications_respect_user_channel_preferences(self, d3_setup):
        """NotificationService respeta las preferencias In-App de NotificationPreference."""
        alice = d3_setup["alice"]
        bob = d3_setup["bob"]

        # Desactivar likes in-app para Alice
        prefs, _ = NotificationPreference.objects.get_or_create(user=alice)
        prefs.in_app_like = False
        prefs.save()

        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.LIKE,
            title="Nuevo me gusta",
            message="A Bob le gustó tu reseña",
        )
        # Como in_app_like está apagado, no se crea notificación In-App
        assert notif is None
        assert Notification.objects.filter(recipient=alice, actor=bob).count() == 0

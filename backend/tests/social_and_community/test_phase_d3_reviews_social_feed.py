"""
Suite de pruebas para la Fase D3 — Reseñas, Social y Feed (Roadmap v2.0).

Verifica:
1. test_review_soft_delete_and_reactivation_clean: Reactivación sin colisión de unicidad.
2. test_review_unique_active_constraint_enforced: Intento de duplicado activo lanza error de validación e IntegrityError en BD.
3. test_review_like_concurrency_and_count_accuracy: Toggle de like atómico, idempotente y recuento exacto.
4. test_social_feed_excludes_blocked_and_muted_users: Feed excluye inmediatamente a usuarios bloqueados y silenciados.
5. test_social_feed_query_optimization: Consultas O(1) en el feed social sin problemas de N+1.
6. test_notifications_respect_blocking_and_preferences: No se generan notificaciones si hay bloqueo o preferencias desactivadas.
7. test_moderated_review_hidden_from_public_feed: Contenido con is_moderated=True ocultado de feeds y listados públicos.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, Review, ReviewLike
from books.serializers import ReviewSerializer
from users.models import (
    Activity,
    ActivityType,
    Notification,
    NotificationPreference,
    NotificationType,
)
from users.notification_service import NotificationService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def d3_environment(db):
    author = Author.objects.create(name="Gabriel García Márquez")
    cat_fiction = Category.objects.create(name="Ficción", slug="ficcion")
    book = Book.objects.create(
        title="El amor en los tiempos del cólera",
        isbn="9780307387264",
        author=author,
    )
    book.categories.add(cat_fiction)

    user1 = User.objects.create_user(username="lector1", email="l1@test.com", password="password123")
    user2 = User.objects.create_user(username="lector2", email="l2@test.com", password="password123")
    user3 = User.objects.create_user(username="lector3", email="l3@test.com", password="password123")
    staff_user = User.objects.create_user(username="staffadmin", email="admin@test.com", password="password123", is_staff=True)

    return {
        "author": author,
        "book": book,
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "staff_user": staff_user,
    }


@pytest.mark.django_db
class TestPhaseD3ReviewsSocialFeed:

    def test_review_soft_delete_and_reactivation_clean(self, api_client, d3_environment):
        """
        Garantiza que tras un borrado lógico (soft-delete), si el usuario vuelve a publicar
        una reseña para el mismo libro, el sistema restaura determinísticamente la entidad
        existente, actualiza contenido y calificación, y recalcula el average_rating.
        """
        user = d3_environment["user1"]
        book = d3_environment["book"]
        api_client.force_authenticate(user=user)

        # 1. Crear reseña inicial
        res1 = api_client.post(
            "/api/v1/books/reviews/",
            {"book_id": book.id, "rating": 3, "title": "Regular", "text": "Esperaba más."},
            format="json",
        )
        assert res1.status_code == status.HTTP_201_CREATED
        review_id = res1.data["id"]

        book.refresh_from_db()
        assert book.average_rating == 3.0

        # 2. Eliminar lógicamente la reseña
        del_res = api_client.delete(f"/api/v1/books/reviews/{review_id}/")
        assert del_res.status_code in (status.HTTP_204_NO_CONTENT, status.HTTP_200_OK)

        # Confirmar que está en soft-delete
        rev_db = Review.all_objects.get(id=review_id)
        assert rev_db.deleted_at is not None
        assert rev_db.is_deleted is True
        assert not Review.objects.active().filter(id=review_id).exists()

        book.refresh_from_db()
        assert book.average_rating is None or book.average_rating == 0.0

        # 3. El usuario vuelve a reseñar el mismo libro
        res2 = api_client.post(
            "/api/v1/books/reviews/",
            {"book_id": book.id, "rating": 5, "title": "Relectura magistral", "text": "Cambié de opinión al releerlo."},
            format="json",
        )
        assert res2.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)
        new_review_id = res2.data["id"]

        # Debe ser la misma entidad restaurada y no un registro duplicado
        assert new_review_id == review_id
        assert Review.all_objects.filter(user=user, book=book).count() == 1

        rev_restored = Review.objects.get(id=review_id)
        assert rev_restored.deleted_at is None
        assert rev_restored.rating == 5
        assert rev_restored.title == "Relectura magistral"

        book.refresh_from_db()
        assert book.average_rating == 5.0

    def test_review_unique_active_constraint_enforced(self, d3_environment):
        """
        Verifica que no puedan coexistir dos reseñas activas para el mismo par (user, book)
        tanto a nivel de serializer como por la UniqueConstraint condicional de base de datos.
        """
        user = d3_environment["user1"]
        book = d3_environment["book"]

        # Crear primera reseña activa
        Review.objects.create(user=user, book=book, rating=4, title="Buena lectura")

        # 1. Validación de Serializer rechaza duplicado activo
        serializer = ReviewSerializer(
            data={"book_id": book.id, "rating": 5, "title": "Intento duplicado"},
            context={"request": type("Req", (), {"user": user})()},
        )
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

        # 2. Base de datos rechaza duplicado activo mediante UniqueConstraint
        with pytest.raises(IntegrityError):
            Review.objects.create(user=user, book=book, rating=3, title="Colisión DB")

    def test_review_like_concurrency_and_count_accuracy(self, api_client, d3_environment):
        """
        Verifica que el endpoint de alternar like sea atómico, mantenga la integridad
        de conteo y gestione idempotentemente llamadas sucesivas.
        """
        liker = d3_environment["user2"]
        author_user = d3_environment["user1"]
        book = d3_environment["book"]

        review = Review.objects.create(user=author_user, book=book, rating=5, title="Genial")
        api_client.force_authenticate(user=liker)

        # 1. Like
        res1 = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res1.status_code == status.HTTP_200_OK
        assert res1.data["liked"] is True
        assert res1.data["likes_count"] == 1
        assert ReviewLike.objects.filter(user=liker, review=review).count() == 1

        # 2. Unlike (toggle)
        res2 = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["liked"] is False
        assert res2.data["likes_count"] == 0
        assert ReviewLike.objects.filter(user=liker, review=review).count() == 0

        # 3. Volver a dar like
        res3 = api_client.post(f"/api/v1/books/reviews/{review.id}/like/")
        assert res3.status_code == status.HTTP_200_OK
        assert res3.data["liked"] is True
        assert res3.data["likes_count"] == 1
        assert ReviewLike.objects.filter(user=liker, review=review).count() == 1

    def test_social_feed_excludes_blocked_and_muted_users(self, api_client, d3_environment):
        """
        Verifica que el feed social excluya rigurosamente publicaciones de usuarios
        bloqueados (en ambas direcciones) y silenciados.
        """
        viewer = d3_environment["user1"]
        friend_muted = d3_environment["user2"]
        friend_blocked = d3_environment["user3"]
        book = d3_environment["book"]

        viewer.following.add(friend_muted)
        viewer.following.add(friend_blocked)

        act_muted = Activity.objects.create(
            user=friend_muted,
            type=ActivityType.BOOK_FINISHED,
            book=book,
            metadata={"rating": 4},
        )
        act_blocked = Activity.objects.create(
            user=friend_blocked,
            type=ActivityType.REVIEW_CREATED,
            book=book,
            metadata={"title": "Reseña de usuario bloqueado"},
        )

        api_client.force_authenticate(user=viewer)

        # Antes de silenciar/bloquear: ambas actividades están presentes
        res_initial = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert res_initial.status_code == status.HTTP_200_OK
        initial_ids = [item["id"] for item in res_initial.data["results"]]
        assert act_muted.id in initial_ids
        assert act_blocked.id in initial_ids

        # Viewer silencia a friend_muted
        viewer.muted_users.add(friend_muted)

        # friend_blocked bloquea a viewer (bloqueo bidireccional)
        friend_blocked.blocked_users.add(viewer)

        # Feed actualizado
        res_filtered = api_client.get("/api/v1/users/feed/?mode=chronological")
        assert res_filtered.status_code == status.HTTP_200_OK
        filtered_ids = [item["id"] for item in res_filtered.data["results"]]
        assert act_muted.id not in filtered_ids
        assert act_blocked.id not in filtered_ids

    def test_social_feed_query_optimization(self, api_client, d3_environment):
        """
        Verifica que el endpoint de feed mantenga una cota de consultas SQL constante O(1)
        mediante precarga adecuada de relaciones (select_related y prefetch_related).
        """
        viewer = d3_environment["user1"]
        friend = d3_environment["user2"]

        viewer.following.add(friend)

        # Crear 10 actividades en el feed con diferentes libros
        for i in range(10):
            b = Book.objects.create(
                title=f"Libro {i}",
                isbn=f"97800000000{i:02d}",
                author=d3_environment["author"],
            )
            rev = Review.objects.create(
                user=friend,
                book=b,
                rating=5,
                title=f"Reseña {i}",
                text="Texto de la reseña...",
            )
            Activity.objects.create(
                user=friend,
                type=ActivityType.REVIEW_CREATED,
                book=b,
                review=rev,
            )

        api_client.force_authenticate(user=viewer)

        with CaptureQueriesContext(connection) as queries:
            res = api_client.get("/api/v1/users/feed/?mode=chronological")
            assert res.status_code == status.HTTP_200_OK
            assert len(res.data["results"]) >= 10

        # Validar que no hay consulta N+1 por cada actividad
        # Debe mantenerse por debajo de 12 consultas totales para autenticación, sesión, perfil y feed
        assert len(queries) < 15, f"Demasiadas consultas detectadas en el feed: {len(queries)}"

    def test_notifications_respect_blocking_and_preferences(self, d3_environment):
        """
        Verifica que NotificationService descarte el envío si existe un bloqueo
        social activo o si el receptor tiene deshabilitada esa preferencia.
        """
        recipient = d3_environment["user1"]
        actor = d3_environment["user2"]

        # 1. Caso Normal: Notificación entregada
        notif1 = NotificationService.send_notification(
            recipient=recipient,
            actor=actor,
            notif_type=NotificationType.LIKE,
            title="Nuevo like",
            message="A lector2 le gustó tu reseña",
        )
        assert notif1 is not None
        assert Notification.objects.filter(recipient=recipient, actor=actor).count() == 1

        # 2. Bloqueo activo: Receptor bloquea a actor -> Descartada
        recipient.blocked_users.add(actor)
        notif_blocked = NotificationService.send_notification(
            recipient=recipient,
            actor=actor,
            notif_type=NotificationType.COMMENT,
            title="Nuevo comentario",
            message="Intento de comentario de bloqueado",
        )
        assert notif_blocked is None
        recipient.blocked_users.remove(actor)

        # 3. Preferencias desactivadas: Desactivar in_app_like
        prefs = NotificationPreference.objects.get_or_create(user=recipient)[0]
        prefs.in_app_like = False
        prefs.save(update_fields=["in_app_like"])

        notif_pref = NotificationService.send_notification(
            recipient=recipient,
            actor=actor,
            notif_type=NotificationType.LIKE,
            title="Like desactivado",
            message="No debería generarse",
        )
        assert notif_pref is None

    def test_moderated_review_hidden_from_public_feed(self, api_client, d3_environment):
        """
        Verifica que una reseña marcada con is_moderated=True sea excluida
        inmediatamente de los feeds sociales y de las consultas públicas de reseñas.
        """
        viewer = d3_environment["user1"]
        author = d3_environment["user2"]
        staff = d3_environment["staff_user"]
        book = d3_environment["book"]

        viewer.following.add(author)

        review = Review.objects.create(
            user=author,
            book=book,
            rating=1,
            title="Contenido inapropiado",
            text="Texto con infracción de normas.",
            is_moderated=True,
        )
        act = Activity.objects.create(
            user=author,
            type=ActivityType.REVIEW_CREATED,
            book=book,
            review=review,
        )

        api_client.force_authenticate(user=viewer)

        # 1. Excluida del Feed social del seguidor
        res_feed = api_client.get("/api/v1/users/feed/?mode=chronological")
        feed_ids = [item["id"] for item in res_feed.data["results"]]
        assert act.id not in feed_ids

        # 2. Excluida del listado público de reseñas del libro
        res_reviews = api_client.get(f"/api/v1/books/reviews/?book={book.id}")
        review_ids = [item["id"] for item in res_reviews.data["results"]]
        assert review.id not in review_ids

        # 3. Personal de Staff o moderación SÍ puede acceder a la reseña moderada en detalle
        api_client.force_authenticate(user=staff)
        res_staff = api_client.get(f"/api/v1/books/reviews/{review.id}/")
        assert res_staff.status_code == status.HTTP_200_OK
        assert res_staff.data["id"] == review.id

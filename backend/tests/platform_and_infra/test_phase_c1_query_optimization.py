"""
Suite de Pruebas de Optimización de Consultas y Erradicación de N+1 (Fase C1)
Valida con CaptureQueriesContext que los endpoints de alto tráfico del catálogo,
muro social, feed de actividades y listas mantienen complejidad O(1) en queries.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingList, ReadingListItem, Review
from users.models import Activity, ActivityType, UserPost, UserPostComment, UserPostLike

User = get_user_model()


@pytest.mark.django_db
class TestPhaseC1QueryOptimization:
    """Valida la erradicación estricta de consultas N+1 en vistas de alto tráfico."""

    def test_book_list_query_count_is_constant(self):
        """
        Comprueba que listar libros en BookListCreateView tiene complejidad O(1):
        El número de queries debe ser idéntico al listar 3 libros que al listar 10 libros.
        """
        author = Author.objects.create(name="Gabriel García Márquez")
        cat1 = Category.objects.create(name="Ficción", slug="ficcion")
        cat2 = Category.objects.create(name="Clásicos", slug="clasicos")

        # Crear lote 1: 3 libros
        books_batch_1 = []
        for i in range(3):
            b = Book.objects.create(
                title=f"Libro Lote 1 #{i}",
                author=author,
                isbn=f"978000000000{i}",
            )
            b.categories.add(cat1, cat2)
            b.authors.add(author)
            books_batch_1.append(b)

        client = APIClient()

        # Medir queries para lote 1
        with CaptureQueriesContext(connection) as ctx_1:
            res_1 = client.get('/api/v1/books/')
            assert res_1.status_code == status.HTTP_200_OK

        queries_count_1 = len(ctx_1)

        # Crear lote 2: 7 libros adicionales (total 10)
        for i in range(3, 10):
            b = Book.objects.create(
                title=f"Libro Lote 2 #{i}",
                author=author,
                isbn=f"978000000001{i}",
            )
            b.categories.add(cat1, cat2)
            b.authors.add(author)

        # Medir queries para lote 2
        with CaptureQueriesContext(connection) as ctx_2:
            res_2 = client.get('/api/v1/books/')
            assert res_2.status_code == status.HTTP_200_OK

        queries_count_2 = len(ctx_2)

        # El número de queries no debe escalar con el número de libros
        assert queries_count_1 == queries_count_2, (
            f"Se detectó N+1 en /api/v1/books/: {queries_count_1} queries para 3 libros, "
            f"{queries_count_2} queries para 10 libros."
        )

    def test_social_feed_query_count_is_constant(self):
        """
        Comprueba que FeedView mantenga complejidad O(1) de consultas
        independientemente del número de actividades recuperadas.
        """
        user_viewer = User.objects.create_user(
            username="feed_viewer", email="viewer@mybooksocial.com", password="PassWord123!"
        )
        user_friend = User.objects.create_user(
            username="feed_friend", email="friend@mybooksocial.com", password="PassWord123!"
        )
        user_viewer.following.add(user_friend)

        author = Author.objects.create(name="Jane Austen")
        book = Book.objects.create(title="Orgullo y Prejuicio", author=author, isbn="9780141439518")

        # Crear 2 actividades iniciales
        for i in range(2):
            Activity.objects.create(
                user=user_friend,
                type=ActivityType.BOOK_ADDED,
                book=book,
            )

        client = APIClient()
        client.force_authenticate(user=user_viewer)

        with CaptureQueriesContext(connection) as ctx_1:
            res_1 = client.get('/api/v1/users/feed/')
            assert res_1.status_code == status.HTTP_200_OK

        queries_1 = len(ctx_1)

        # Añadir 6 actividades más (total 8)
        for i in range(2, 8):
            Activity.objects.create(
                user=user_friend,
                type=ActivityType.BOOK_ADDED,
                book=book,
            )

        with CaptureQueriesContext(connection) as ctx_2:
            res_2 = client.get('/api/v1/users/feed/')
            assert res_2.status_code == status.HTTP_200_OK

        queries_2 = len(ctx_2)

        assert queries_1 == queries_2, (
            f"Se detectó N+1 en /api/v1/users/feed/: {queries_1} queries para 2 actividades, "
            f"{queries_2} queries para 8 actividades."
        )

    def test_user_posts_query_count_is_constant(self):
        """
        Comprueba que UserPostListCreateView mantenga consultas O(1)
        al renderizar publicaciones con likes y comentarios anidados.
        """
        owner = User.objects.create_user(
            username="profile_owner", email="owner@mybooksocial.com", password="PassWord123!"
        )
        commenter = User.objects.create_user(
            username="commenter", email="commenter@mybooksocial.com", password="PassWord123!"
        )

        author = Author.objects.create(name="Frank Herbert")
        book = Book.objects.create(title="Dune", author=author, isbn="9780441172719")

        # Crear 2 publicaciones iniciales con comentarios y likes
        posts_batch = []
        for i in range(2):
            post = UserPost.objects.create(
                author=owner,
                target_user=owner,
                content=f"Publicación #{i}",
                book=book,
            )
            UserPostComment.objects.create(post=post, user=commenter, text="Gran lectura!")
            UserPostLike.objects.create(post=post, user=commenter)
            posts_batch.append(post)

        client = APIClient()
        client.force_authenticate(user=owner)

        with CaptureQueriesContext(connection) as ctx_1:
            res_1 = client.get(f'/api/v1/users/{owner.id}/posts/')
            assert res_1.status_code == status.HTTP_200_OK

        queries_1 = len(ctx_1)

        # Crear 5 publicaciones más con comentarios y likes (total 7)
        for i in range(2, 7):
            post = UserPost.objects.create(
                author=owner,
                target_user=owner,
                content=f"Publicación #{i}",
                book=book,
            )
            UserPostComment.objects.create(post=post, user=commenter, text="Gran lectura!")
            UserPostLike.objects.create(post=post, user=commenter)

        with CaptureQueriesContext(connection) as ctx_2:
            res_2 = client.get(f'/api/v1/users/{owner.id}/posts/')
            assert res_2.status_code == status.HTTP_200_OK

        queries_2 = len(ctx_2)

        assert queries_1 == queries_2, (
            f"Se detectó N+1 en /api/v1/users/<id>/posts/: {queries_1} queries para 2 posts, "
            f"{queries_2} queries para 7 posts."
        )

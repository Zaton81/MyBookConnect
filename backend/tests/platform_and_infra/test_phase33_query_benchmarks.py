import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from books.models import Book, Author, Category, Review
from users.models import UserPost, UserPostComment, UserPostLike

User = get_user_model()


@pytest.mark.django_db
class TestPhase33QueryBenchmarks:
    """
    Suite de benchmarks de rendimiento y control estricto de consultas (N+1 prevention).
    Verifica que las vistas clave mantengan un número constante O(1) de consultas a PostgreSQL
    sin importar el número de entidades o relaciones hijas renderizadas.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="benchmark_user",
            email="benchmark@example.com",
            password="BenchPassword123!"
        )
        self.client.force_authenticate(user=self.user)

    def test_user_posts_wall_query_count_is_constant_o1(self):
        """
        Verifica que GET /api/v1/users/<id>/posts/ mantenga consultas O(1) con likes, comentarios y libros.
        """
        author = Author.objects.create(name="Escritor de Muro")
        book = Book.objects.create(title="Libro en Muro", author=author)
        commenter = User.objects.create_user(username="commenter", email="com@example.com", password="Pass123!Secure")

        for i in range(2):
            post = UserPost.objects.create(author=self.user, target_user=self.user, content=f"Post {i}", book=book)
            UserPostLike.objects.create(post=post, user=commenter)
            UserPostComment.objects.create(post=post, user=commenter, text="Gran lectura")

        with CaptureQueriesContext(connection) as captured_2:
            res_2 = self.client.get(f"/api/v1/users/{self.user.id}/posts/")
            assert res_2.status_code == status.HTTP_200_OK

        count_for_2 = len(captured_2.captured_queries)

        # Crear 6 posts adicionales con likes y comentarios
        for i in range(2, 8):
            post = UserPost.objects.create(author=self.user, target_user=self.user, content=f"Post Extra {i}", book=book)
            UserPostLike.objects.create(post=post, user=commenter)
            UserPostComment.objects.create(post=post, user=commenter, text="Gran lectura")

        with CaptureQueriesContext(connection) as captured_8:
            res_8 = self.client.get(f"/api/v1/users/{self.user.id}/posts/")
            assert res_8.status_code == status.HTTP_200_OK

        count_for_8 = len(captured_8.captured_queries)

        assert count_for_8 == count_for_2, (
            f"Posible problema N+1 en muro de publicaciones: {count_for_2} queries con 2 posts vs {count_for_8} queries con 8 posts."
        )

    def test_reviews_list_for_book_query_count_is_constant_o1(self):
        """
        Verifica que GET /api/v1/reviews/?book=<id> mantenga consultas acotadas O(1) independientemente del volumen.
        """
        cat = Category.objects.create(name="Filosofía", slug="filosofia")
        author = Author.objects.create(name="Filósofo")
        book = Book.objects.create(title="Tratado Principal", author=author)
        book.categories.add(cat)
        book.authors.add(author)

        for i in range(2):
            reviewer = User.objects.create_user(username=f"reviewer_bench_{i}", email=f"rev_{i}@example.com", password="Pass123!Secure")
            Review.objects.create(user=reviewer, book=book, rating=4, title=f"Review {i}", text="Contenido")

        with CaptureQueriesContext(connection) as captured_2:
            res_2 = self.client.get(f"/api/v1/reviews/?book={book.id}")
            assert res_2.status_code == status.HTTP_200_OK

        count_for_2 = len(captured_2.captured_queries)

        for i in range(2, 8):
            reviewer = User.objects.create_user(username=f"reviewer_bench_{i}", email=f"rev_{i}@example.com", password="Pass123!Secure")
            Review.objects.create(user=reviewer, book=book, rating=5, title=f"Review Extra {i}", text="Contenido")

        with CaptureQueriesContext(connection) as captured_8:
            res_8 = self.client.get(f"/api/v1/reviews/?book={book.id}")
            assert res_8.status_code == status.HTTP_200_OK

        count_for_8 = len(captured_8.captured_queries)

        assert count_for_8 == count_for_2, (
            f"Posible problema N+1 en listado de reseñas por libro: {count_for_2} queries vs {count_for_8} queries."
        )

    def test_feed_query_count_is_constant_o1(self):
        """
        Verifica que GET /api/v1/auth/feed/ se mantenga O(1) ante incremento de actividades.
        """
        author = Author.objects.create(name="Autor Feed")
        b = Book.objects.create(title="Libro de Feed", author=author)

        with CaptureQueriesContext(connection) as captured_initial:
            res_init = self.client.get("/api/v1/auth/feed/")
            assert res_init.status_code == status.HTTP_200_OK

        count_initial = len(captured_initial.captured_queries)

        # Crear actividades en el feed (posts y reviews)
        for i in range(5):
            UserPost.objects.create(author=self.user, target_user=self.user, content=f"Feed Post {i}", book=b)

        with CaptureQueriesContext(connection) as captured_after:
            res_after = self.client.get("/api/v1/auth/feed/")
            assert res_after.status_code == status.HTTP_200_OK

        count_after = len(captured_after.captured_queries)

        assert count_after == count_initial, (
            f"Posible problema N+1 en feed social: {count_initial} queries vs {count_after} queries."
        )

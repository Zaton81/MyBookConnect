"""
Suite de pruebas automatizadas para la Fase 20 — Descubrimiento de libros.
Verifica endpoints de descubrimiento público, tendencias sin autenticación forzada,
filtrado facetado por género, caché en Redis y estadísticas para la Landing Page.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, Review, UserBook

UserModel = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def discovery_data(db):
    # Crear categorías
    cat_scifi = Category.objects.create(name="Ciencia Ficción", slug="ciencia-ficcion")
    cat_fantasy = Category.objects.create(name="Fantasía", slug="fantasia")
    cat_thriller = Category.objects.create(name="Thriller", slug="thriller")

    # Crear autores
    author1 = Author.objects.create(name="Isaac Asimov")
    author2 = Author.objects.create(name="Brandon Sanderson")

    # Crear libros
    book1 = Book.objects.create(
        title="Fundación",
        isbn="9780553293357",
        author=author1,
        average_rating=4.8,
    )
    book1.categories.add(cat_scifi)

    book2 = Book.objects.create(
        title="El Camino de los Reyes",
        isbn="9780765326355",
        author=author2,
        average_rating=4.9,
    )
    book2.categories.add(cat_fantasy)

    book3 = Book.objects.create(
        title="Bóvedas de Acero",
        isbn="9780553803716",
        author=author1,
        average_rating=4.5,
    )
    book3.categories.add(cat_scifi, cat_thriller)

    # Crear usuario para simular lecturas y reviews
    user = UserModel.objects.create_user(
        username="reader_alpha",
        email="alpha@example.com",
        password="ValidPassword123!",
    )
    UserBook.objects.create(user=user, book=book2, status="READ")
    Review.objects.create(user=user, book=book2, rating=5, text="Obra maestra de la fantasía épica.")

    return {
        'cats': [cat_scifi, cat_fantasy, cat_thriller],
        'books': [book1, book2, book3],
        'user': user,
    }


@pytest.mark.django_db
class TestPhase20BookDiscovery:
    """Verificación de especificaciones de descubrimiento de libros (Fase 20)."""

    def test_anonymous_access_to_discover_endpoint(self, api_client, discovery_data):
        """Un usuario anónimo debe poder consultar el endpoint de descubrimiento sin 401."""
        response = api_client.get("/api/v1/books/discover/")
        assert response.status_code == status.HTTP_200_OK

        payload = response.json()
        assert "trending" in payload
        assert "popular" in payload
        assert "newest" in payload
        assert "categories" in payload
        assert "stats" in payload

        # Verificar contenido de categorías
        cat_names = [c["name"] for c in payload["categories"]]
        assert "Ciencia Ficción" in cat_names
        assert "Fantasía" in cat_names

        # Verificar estadísticas de la comunidad para la Landing
        assert payload["stats"]["total_books"] >= 3
        assert payload["stats"]["total_reviews"] >= 1

    def test_trending_books_endpoint_allow_any(self, api_client, discovery_data):
        """TrendingBooksView debe ser accesible por visitantes anónimos."""
        response = api_client.get("/api/v1/books/trending/")
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert "results" in payload
        assert "period" in payload

    def test_discover_filter_by_genre(self, api_client, discovery_data):
        """Filtrar por género devuelve libros pertinentes y el género activo."""
        scifi_cat = discovery_data['cats'][0]
        response = api_client.get(f"/api/v1/books/discover/?genre={scifi_cat.slug}")
        assert response.status_code == status.HTTP_200_OK

        payload = response.json()
        assert payload["active_genre"] == "Ciencia Ficción"
        assert len(payload["genre_books"]) >= 1
        scifi_titles = [b["title"] for b in payload["genre_books"]]
        assert "Fundación" in scifi_titles

    def test_discover_limit_parameter_respected(self, api_client, discovery_data):
        """El parámetro ?limit debe ser respetado y acotado razonablemente."""
        response = api_client.get("/api/v1/books/discover/?limit=2")
        assert response.status_code == status.HTTP_200_OK
        payload = response.json()
        assert len(payload["popular"]) <= 2
        assert len(payload["newest"]) <= 2

    def test_discover_cached_in_redis(self, api_client, discovery_data):
        """Las peticiones subsecuentes deben responder limpiamente aprovechando la caché."""
        res1 = api_client.get("/api/v1/books/discover/")
        assert res1.status_code == status.HTTP_200_OK

        res2 = api_client.get("/api/v1/books/discover/")
        assert res2.status_code == status.HTTP_200_OK
        assert res1.json() == res2.json()

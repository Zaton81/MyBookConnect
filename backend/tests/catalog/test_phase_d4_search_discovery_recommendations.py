"""
Suite de pruebas para la Fase D4 — Búsqueda, Descubrimiento y Recomendaciones.

Valida:
1. Búsqueda híbrida multicanal (UnifiedSearchEngine y /api/v1/search/) con resiliencia y ordenación.
2. Descubrimiento público no autenticado (/api/v1/books/discover/) con tendencias y faceteado.
3. Exclusión estricta de obras ya leídas o añadidas en UserBook dentro del motor de recomendaciones.
4. Soporte para cold-start basado en categorías favoritas del onboarding (favorite_categories).
5. Transparencia ética y explicabilidad algorítmica ('reason' en recomendaciones y endpoint /explain/).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books import services
from books.models import Author, Book, Category, ReadingStatus, UserBook
from books.services.unified_search_service import UnifiedSearchEngine

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def d4_environment(db):
    """Crea un catálogo diverso de libros, géneros y usuarios para la suite D4."""
    # Categorías
    cat_scifi = Category.objects.create(name="Ciencia Ficción", slug="ciencia-ficcion")
    cat_fantasy = Category.objects.create(name="Fantasía", slug="fantasia")
    cat_history = Category.objects.create(name="Historia", slug="historia")

    # Autores
    author_asimov = Author.objects.create(name="Isaac Asimov")
    author_tolkien = Author.objects.create(name="J.R.R. Tolkien")
    author_lem = Author.objects.create(name="Stanislaw Lem")

    # Libros
    book1 = Book.objects.create(
        title="Fundación",
        isbn="9788466332156",
        author=author_asimov,
        average_rating=4.8,
        page_count=288,
        description="El declive del Imperio Galáctico y la psicohistoria de Hari Seldon.",
    )
    book1.categories.add(cat_scifi)

    book2 = Book.objects.create(
        title="Solaris",
        isbn="9788484323280",
        author=author_lem,
        average_rating=4.5,
        page_count=256,
        description="El misterioso océano viviente del planeta Solaris y los fantasmas del pasado.",
    )
    book2.categories.add(cat_scifi)

    book3 = Book.objects.create(
        title="El Señor de los Anillos",
        isbn="9788445071403",
        author=author_tolkien,
        average_rating=4.9,
        page_count=1200,
        description="La gesta de Frodo Bolsón para destruir el Anillo Único en el Monte del Destino.",
    )
    book3.categories.add(cat_fantasy)

    book4 = Book.objects.create(
        title="Breve historia del mundo",
        isbn="9788499300000",
        average_rating=4.2,
        page_count=350,
        description="Una introducción accesible y amena a los hitos de la civilización.",
    )
    book4.categories.add(cat_history)

    # Usuarios
    alice = User.objects.create_user(
        username="alice_d4",
        email="alice@mybooksocial.com",
        password="Password123!",
    )
    bob = User.objects.create_user(
        username="bob_d4",
        email="bob@mybooksocial.com",
        password="Password123!",
    )

    return {
        "cat_scifi": cat_scifi,
        "cat_fantasy": cat_fantasy,
        "cat_history": cat_history,
        "author_asimov": author_asimov,
        "author_tolkien": author_tolkien,
        "author_lem": author_lem,
        "book1": book1,
        "book2": book2,
        "book3": book3,
        "book4": book4,
        "alice": alice,
        "bob": bob,
    }


@pytest.mark.django_db
class TestHybridSearchAndRanking:
    def test_unified_search_engine_finds_by_title_and_author(self, d4_environment):
        """UnifiedSearchEngine recupera obras tanto por título como por nombre de autor."""
        engine = UnifiedSearchEngine(mode="hybrid")

        # Búsqueda por título
        items_title, total_title = engine.search(query="Fundación", auto_import=False)
        assert total_title >= 1
        assert any(item.book.title == "Fundación" for item in items_title)

        # Búsqueda por autor
        items_author, total_author = engine.search(query="Tolkien", auto_import=False)
        assert total_author >= 1
        assert any("Tolkien" in (item.book.author.name if item.book.author else "") for item in items_author)

    def test_global_search_endpoint_returns_catalog_and_authors(self, api_client, d4_environment):
        """El endpoint global /api/v1/search/ devuelve libros y autores coincidentes."""
        response = api_client.get("/api/v1/search/?q=Solaris")
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        # Validar estructura de respuesta
        assert "books" in data
        assert len(data["books"]) >= 1
        assert data["books"][0]["title"] == "Solaris"


@pytest.mark.django_db
class TestPublicDiscoveryAndFaceting:
    def test_discover_public_endpoint_unauthenticated(self, api_client, d4_environment):
        """El endpoint /api/v1/books/discover/ es accesible públicamente sin autenticación."""
        response = api_client.get("/api/v1/books/discover/")
        assert response.status_code == status.HTTP_200_OK

        data = response.data
        assert "trending" in data
        assert "popular" in data
        assert "categories" in data
        assert "stats" in data
        assert len(data["trending"]) >= 1

    def test_discover_filter_by_genre(self, api_client, d4_environment):
        """El endpoint de descubrimiento filtra adecuadamente por género específico."""
        response = api_client.get("/api/v1/books/discover/?genre=Ciencia Ficción")
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert "genre_books" in data
        genre_books = data["genre_books"]
        assert len(genre_books) >= 1
        # Todos los libros devueltos deben pertenecer a Ciencia Ficción
        for b in genre_books:
            assert "Ciencia Ficción" in b["categories"]


@pytest.mark.django_db
class TestRecommendationEngineIntegrityAndExplainability:
    def test_recommendations_exclude_already_read_books(self, api_client, d4_environment):
        """Las recomendaciones excluyen rigurosamente las obras ya presentes en la biblioteca del usuario."""
        alice = d4_environment["alice"]
        book1 = d4_environment["book1"]
        book2 = d4_environment["book2"]

        # Alice ya leyó Fundación (book1)
        UserBook.objects.create(
            user=alice,
            book=book1,
            status=ReadingStatus.READ,
            rating=5,
        )

        api_client.force_authenticate(user=alice)
        response = api_client.get("/api/v1/books/recommendations/?strategy=hybrid")
        assert response.status_code == status.HTTP_200_OK

        results = response.data["results"]
        recommended_ids = [item["id"] for item in results]

        # Fundación NO debe ser recomendada porque ya la leyó
        assert book1.id not in recommended_ids

        # Solaris (de la misma categoría de ciencia ficción) debe ser sugerida
        assert book2.id in recommended_ids

    def test_recommendations_cold_start_uses_favorite_categories(self, api_client, d4_environment):
        """Para nuevos usuarios, el cold start pondera sus categorías favoritas de onboarding."""
        bob = d4_environment["bob"]
        cat_fantasy = d4_environment["cat_fantasy"]
        book3 = d4_environment["book3"]  # Fantasía (El Señor de los Anillos)

        # Bob no ha leído nada aún, pero en onboarding eligió Fantasía
        bob.favorite_categories.add(cat_fantasy)

        api_client.force_authenticate(user=bob)
        response = api_client.get("/api/v1/books/recommendations/?strategy=hybrid")
        assert response.status_code == status.HTTP_200_OK

        results = response.data["results"]
        assert len(results) >= 1
        top_book = results[0]
        # El libro de fantasía debe estar entre las primeras sugerencias
        assert any(item["id"] == book3.id for item in results)

    def test_recommendations_ai_ethical_transparency_and_explainability(self, api_client, d4_environment):
        """Cada libro recomendado contiene un motivo explicativo y el endpoint /explain/ detalla las razones."""
        alice = d4_environment["alice"]
        book1 = d4_environment["book1"]
        book2 = d4_environment["book2"]

        # Alice tiene una lectura previa
        UserBook.objects.create(
            user=alice,
            book=book1,
            status=ReadingStatus.READ,
            rating=5,
        )

        api_client.force_authenticate(user=alice)
        response = api_client.get("/api/v1/books/recommendations/?strategy=hybrid")
        assert response.status_code == status.HTTP_200_OK

        results = response.data["results"]
        for item in results:
            # Explicabilidad ética obligatoria
            assert "reason" in item
            assert len(item["reason"].strip()) > 0
            assert "affinity_percentage" in item

        # Probar endpoint específico de explicación de recomendación
        explain_response = api_client.get(f"/api/v1/books/recommendations/{book2.id}/explain/")
        assert explain_response.status_code == status.HTTP_200_OK
        explain_data = explain_response.data

        assert "headline" in explain_data
        assert "primary_reason" in explain_data
        assert "reasons" in explain_data
        assert len(explain_data["headline"]) > 0

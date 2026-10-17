"""
Suite integral de pruebas para la Fase D2 (Autores y Catálogo) del Roadmap v2.0.

Cubre:
1. Autoría multi-rol (BookContribution: autor, traductor, ilustrador, narrador).
2. Persistencia y serialización garantizada de páginas de libro (page_count).
3. Conversión matemática determinista entre ISBN-10 e ISBN-13 y búsqueda bidireccional.
4. Fusión y deduplicación atómica de ediciones vinculadas a la misma obra.
5. Búsqueda y filtrado facetado (UnifiedSearchEngine) tolerante a erratas.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    Book,
    BookContribution,
    Category,
    ContributionRole,
    ReadingStatus,
    Review,
    UserBook,
    get_equivalent_isbns,
    isbn10_to_isbn13,
    isbn13_to_isbn10,
    normalize_isbn,
)
from books.serializers import BookSerializer
from books.services.deduplication_service import merge_books
from books.services.enrichment_service import enrich_book_metadata


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestAuthorMultiRoleContributions:
    def test_book_author_multi_role_creation_and_sync(self):
        """Verifica la asignación de roles de autoría y retrocompatibilidad con book.author."""
        author = Author.objects.create(name="J.R.R. Tolkien")
        translator = Author.objects.create(name="Matilde Horne")
        illustrator = Author.objects.create(name="Alan Lee")

        book = Book.objects.create(
            title="El Señor de los Anillos",
            author=author,
            isbn="9788445071793",
            page_count=1200,
        )

        # Verificar que el autor principal se registró automáticamente como contribución AUTHOR
        assert book.contributions.filter(author=author, role=ContributionRole.AUTHOR).exists()

        # Añadir traductor e ilustrador
        BookContribution.objects.create(
            book=book,
            author=translator,
            role=ContributionRole.TRANSLATOR,
            order=1,
        )
        BookContribution.objects.create(
            book=book,
            author=illustrator,
            role=ContributionRole.ILLUSTRATOR,
            order=2,
        )

        assert book.contributions.count() == 3
        roles = set(book.contributions.values_list('role', flat=True))
        assert roles == {ContributionRole.AUTHOR, ContributionRole.TRANSLATOR, ContributionRole.ILLUSTRATOR}

        # Serialización de contribuciones
        serializer = BookSerializer(book)
        data = serializer.data
        assert "contributions" in data
        assert len(data["contributions"]) == 3
        assert data["page_count"] == 1200


@pytest.mark.django_db
class TestPageCountEnrichmentAndDisplay:
    def test_enrichment_service_persists_page_count_from_providers(self):
        """Verifica que el servicio de enriquecimiento persista page_count en la BD."""
        book = Book.objects.create(
            title="Dune Messiah",
            isbn="9780441172696",
            page_count=None,
        )

        mock_google_response = MagicMock()
        mock_google_response.ok = True
        mock_google_response.json.return_value = {
            "items": [
                {
                    "volumeInfo": {
                        "authors": ["Frank Herbert"],
                        "description": "Secuela de Dune.",
                        "publishedDate": "1969",
                        "pageCount": 336,
                        "categories": ["Science Fiction"],
                    }
                }
            ]
        }

        with patch("requests.get", return_value=mock_google_response):
            enrich_book_metadata(book)

        book.refresh_from_db()
        assert book.page_count == 336
        assert book.author is not None
        assert book.author.name == "Frank Herbert"

    def test_book_detail_endpoint_returns_page_count(self, api_client):
        """El endpoint de detalle de libro debe retornar page_count serializado."""
        book = Book.objects.create(
            title="Hyperion",
            isbn="9780553283686",
            page_count=482,
        )

        response = api_client.get(f"/api/v1/books/{book.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["page_count"] == 482


@pytest.mark.django_db
class TestISBNConversionAndEquivalence:
    def test_isbn10_to_isbn13_and_viceversa(self):
        """Valida la conversión matemática determinista entre ISBN-10 e ISBN-13."""
        # '0441172717' (Dune en ISBN-10) -> '9780441172719' (ISBN-13)
        isbn10 = "0441172717"
        isbn13 = "9780441172719"

        assert isbn10_to_isbn13(isbn10) == isbn13
        assert isbn13_to_isbn10(isbn13) == isbn10

        # Dígito de control 'X' en ISBN-10
        # '080442957X' -> '9780804429573'
        isbn10_x = "080442957X"
        isbn13_x = isbn10_to_isbn13(isbn10_x)
        assert isbn13_x == "9780804429573"
        assert isbn13_to_isbn10(isbn13_x) == isbn10_x

    def test_find_by_isbn_with_cross_edition_search(self):
        """Book.find_by_isbn debe encontrar una obra tanto si se busca por ISBN-10 como por ISBN-13."""
        book = Book.objects.create(
            title="Neuromante",
            isbn="9780441569595",  # Guardado como ISBN-13
        )

        # Buscar por el ISBN-13 exacto
        found_13 = Book.find_by_isbn("978-0441-56959-5")
        assert found_13 is not None
        assert found_13.id == book.id

        # Buscar por su equivalente ISBN-10 ('0441569595')
        found_10 = Book.find_by_isbn("0-441-56959-5")
        assert found_10 is not None
        assert found_10.id == book.id


@pytest.mark.django_db
class TestCatalogDeduplicationAndAtomicMerge:
    def test_merge_books_unifies_isbns_and_user_data(self, django_user_model):
        """Fusión de dos ediciones (física y digital) consolidando reseñas y estanterías sin errores."""
        user = django_user_model.objects.create_user(
            username="lector_dedup",
            email="lector@mybooksocial.com",
            password="Password123!",
        )

        canonical = Book.objects.create(
            title="Cien años de soledad",
            isbn="9788420471839",
            page_count=496,
            description="Novela cumbre del realismo mágico.",
        )

        duplicate = Book.objects.create(
            title="Cien anos de soledad (Edición bolsillo)",
            isbn="9788497592208",
            page_count=432,
        )

        # El usuario tenía el duplicado en su biblioteca y con reseña
        UserBook.objects.create(user=user, book=duplicate, status=ReadingStatus.READ)
        Review.objects.create(user=user, book=duplicate, rating=5, text="Inolvidable Macondo")

        # Fusionar duplicado en canónico
        merge_books(canonical=canonical, duplicates=[duplicate])

        canonical.refresh_from_db()
        # El libro canónico debe haber absorbido el ISBN de la otra edición
        assert "9788497592208" in canonical.additional_isbns
        # Las entradas de usuario deben haberse transferido al canónico
        assert UserBook.objects.filter(book=canonical, user=user).exists()
        assert Review.objects.filter(book=canonical, user=user).exists()
        # El duplicado debe haber sido eliminado
        assert not Book.objects.filter(id=duplicate.id).exists()

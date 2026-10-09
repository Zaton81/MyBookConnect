"""
Pruebas para AmazonBooksProvider, integración de page_count y cadena jerárquica de importación.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from rest_framework.test import APIRequestFactory

from books.models import Book, Author, Publisher
from books.marketplace_models import BookBuyLink
from books.serializers import BookSerializer
from books.services.base import ProviderBookData
from books.services.providers.amazon import AmazonBooksProvider
from books.services.providers.google_books import GoogleBooksProvider
from books.services.providers.openlibrary import OpenLibraryProvider
from books.services.import_service import import_single_by_query, import_multiple_by_title


@pytest.mark.django_db
class TestAmazonBooksProvider:
    """Pruebas unitarias para el proveedor Amazon PA-API v5."""

    def test_amazon_provider_not_configured_by_default(self, settings):
        """Verifica que sin credenciales is_configured() es False y las búsquedas retornan vacío limpiamente."""
        settings.AMAZON_PAAPI_ACCESS_KEY = ""
        settings.AMAZON_PAAPI_SECRET_KEY = ""
        settings.AMAZON_PAAPI_TAG = ""

        provider = AmazonBooksProvider()
        assert provider.is_configured() is False

        # No debe lanzar errores ni hacer llamadas
        results = provider.search_by_title("Cien años de soledad")
        assert results == []

        item = provider.get_by_isbn("9780307474728")
        assert item is None

    def test_amazon_provider_configured_headers(self, settings):
        """Verifica que con credenciales se construyen cabeceras SigV4 conformes."""
        settings.AMAZON_PAAPI_ACCESS_KEY = "AKIAEXAMPLEKEY"
        settings.AMAZON_PAAPI_SECRET_KEY = "SECRETEXAMPLEKEY"
        settings.AMAZON_PAAPI_TAG = "mybookconnect-21"
        settings.AMAZON_PAAPI_REGION = "eu-west-1"
        settings.AMAZON_PAAPI_HOST = "webservices.amazon.es"

        provider = AmazonBooksProvider()
        assert provider.is_configured() is True

        payload = '{"Keywords":"Dune"}'
        headers = provider._build_sigv4_headers("com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems", payload)

        assert "Authorization" in headers
        assert "AWS4-HMAC-SHA256" in headers["Authorization"]
        assert "Credential=AKIAEXAMPLEKEY" in headers["Authorization"]
        assert "SignedHeaders=" in headers["Authorization"]
        assert "Signature=" in headers["Authorization"]
        assert headers["host"] == "webservices.amazon.es"
        assert headers["x-amz-target"] == "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"
        assert "x-amz-date" in headers

    @patch("books.services.providers.amazon.requests.post")
    def test_amazon_provider_search_by_title_success(self, mock_post, settings):
        """Verifica parseo exitoso de SearchItems extrayendo page_count y affiliate_url."""
        settings.AMAZON_PAAPI_ACCESS_KEY = "TEST_KEY"
        settings.AMAZON_PAAPI_SECRET_KEY = "TEST_SECRET"
        settings.AMAZON_PAAPI_TAG = "tag-21"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "SearchResult": {
                "Items": [
                    {
                        "ASIN": "8497592204",
                        "DetailPageURL": "https://www.amazon.es/dp/8497592204?tag=tag-21",
                        "ItemInfo": {
                            "Title": {"DisplayValue": "Cien años de soledad"},
                            "ByLineInfo": {
                                "Contributors": [{"Name": "Gabriel García Márquez", "Role": "Author"}]
                            },
                            "TechnicalInfo": {
                                "NumberOfPages": {"DisplayValue": 496}
                            },
                            "Classifications": {
                                "Binding": {"DisplayValue": "Tapa blanda"}
                            },
                            "ContentInfo": {
                                "PublicationDate": {"DisplayValue": "2003-05-30"}
                            }
                        },
                        "Images": {
                            "Primary": {
                                "Large": {"URL": "https://images-na.ssl-images-amazon.com/images/I/ciensoledad.jpg"}
                            }
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        provider = AmazonBooksProvider()
        results = provider.search_by_title("Cien años de soledad")

        assert len(results) == 1
        book = results[0]
        assert book.title == "Cien años de soledad"
        assert book.author_name == "Gabriel García Márquez"
        assert book.page_count == 496
        assert book.cover_url == "https://images-na.ssl-images-amazon.com/images/I/ciensoledad.jpg"
        assert book.affiliate_url == "https://www.amazon.es/dp/8497592204?tag=tag-21"
        assert book.asin == "8497592204"

    @patch("books.services.providers.amazon.requests.post")
    def test_amazon_provider_get_by_isbn_success(self, mock_post, settings):
        """Verifica parseo de GetItems por ISBN."""
        settings.AMAZON_PAAPI_ACCESS_KEY = "TEST_KEY"
        settings.AMAZON_PAAPI_SECRET_KEY = "TEST_SECRET"
        settings.AMAZON_PAAPI_TAG = "tag-21"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ItemsResult": {
                "Items": [
                    {
                        "ASIN": "8497592204",
                        "DetailPageURL": "https://www.amazon.es/dp/8497592204?tag=tag-21",
                        "ItemInfo": {
                            "Title": {"DisplayValue": "Cien años de soledad"},
                            "ByLineInfo": {"Contributors": [{"Name": "Gabriel García Márquez"}]},
                            "TechnicalInfo": {"NumberOfPages": {"DisplayValue": "496"}},
                        }
                    }
                ]
            }
        }
        mock_post.return_value = mock_response

        provider = AmazonBooksProvider()
        book = provider.get_by_isbn("9788497592208")

        assert book is not None
        assert book.title == "Cien años de soledad"
        assert book.page_count == 496
        assert book.asin == "8497592204"

    @patch("books.services.providers.amazon.requests.post")
    def test_amazon_provider_handles_api_error(self, mock_post, settings):
        """Verifica que errores HTTP o excepciones de red se manejan sin colapsar."""
        settings.AMAZON_PAAPI_ACCESS_KEY = "TEST_KEY"
        settings.AMAZON_PAAPI_SECRET_KEY = "TEST_SECRET"
        settings.AMAZON_PAAPI_TAG = "tag-21"

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = '{"Errors":[{"Code":"TooManyRequests"}]}'
        mock_post.return_value = mock_response

        provider = AmazonBooksProvider()
        assert provider.search_by_title("Dune") == []
        assert provider.get_by_isbn("9780441172719") is None


@pytest.mark.django_db
class TestPageCountProvidersExtraction:
    """Verifica la extracción de número de páginas en Google Books y OpenLibrary."""

    @patch("books.services.providers.google_books.requests.get")
    def test_google_books_extracts_page_count(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "items": [
                {
                    "volumeInfo": {
                        "title": "El nombre del viento",
                        "authors": ["Patrick Rothfuss"],
                        "pageCount": 662,
                        "description": "Una novela fascinante",
                        "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9788401352836"}]
                    }
                }
            ]
        }
        mock_get.return_value = mock_resp

        provider = GoogleBooksProvider()
        results = provider.search_by_title("El nombre del viento")
        assert len(results) == 1
        assert results[0].page_count == 662

    @patch("books.services.providers.openlibrary.requests.get")
    def test_openlibrary_extracts_page_count(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "docs": [
                {
                    "title": "El temor de un hombre sabio",
                    "author_name": ["Patrick Rothfuss"],
                    "number_of_pages_median": 1190,
                    "isbn": ["9788401352331"]
                }
            ]
        }
        mock_get.return_value = mock_resp

        provider = OpenLibraryProvider()
        results = provider.search_by_title("El temor de un hombre sabio")
        assert len(results) == 1
        assert results[0].page_count == 1190


@pytest.mark.django_db
class TestImportHierarchyWithAmazon:
    """Verifica que la cadena de importación prioriza Amazon como opción 1 y hace fallback transparente."""

    @patch.object(AmazonBooksProvider, "is_configured", return_value=True)
    @patch.object(AmazonBooksProvider, "get_by_isbn")
    @patch.object(GoogleBooksProvider, "get_by_isbn")
    def test_import_single_by_query_uses_amazon_first_and_creates_buy_link(
        self, mock_google, mock_amazon, mock_is_conf
    ):
        mock_amazon.return_value = ProviderBookData(
            title="Fahrenheit 451",
            author_name="Ray Bradbury",
            isbn="9788497592451",
            page_count=192,
            asin="849759245X",
            affiliate_url="https://www.amazon.es/dp/849759245X?tag=mybookconnect-21",
        )

        book = import_single_by_query("9788497592451")
        assert book is not None
        assert book.title == "Fahrenheit 451"
        assert book.page_count == 192

        # Google Books NO debió llamarse al encontrar resultado en Amazon
        mock_google.assert_not_called()

        # Debe haberse creado el enlace de afiliado de compra
        buy_links = BookBuyLink.objects.filter(book=book, merchant_name="Amazon")
        assert buy_links.exists()
        assert buy_links.first().url == "https://www.amazon.es/dp/849759245X?tag=mybookconnect-21"
        assert buy_links.first().is_affiliate is True

    @patch.object(AmazonBooksProvider, "is_configured", return_value=False)
    @patch.object(GoogleBooksProvider, "get_by_isbn")
    def test_import_single_by_query_fallbacks_to_google_when_amazon_unconfigured(
        self, mock_google, mock_is_conf
    ):
        mock_google.return_value = ProviderBookData(
            title="1984",
            author_name="George Orwell",
            isbn="9788499890944",
            page_count=326,
            raw_payload={
                "id": "gb1984id",
                "volumeInfo": {
                    "title": "1984",
                    "authors": ["George Orwell"],
                    "pageCount": 326,
                    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9788499890944"}],
                },
            },
        )

        book = import_single_by_query("9788499890944")
        assert book is not None
        assert book.title == "1984"
        assert book.page_count == 326
        mock_google.assert_called_once()

    @patch.object(AmazonBooksProvider, "is_configured", return_value=False)
    @patch.object(GoogleBooksProvider, "search_by_title")
    def test_import_multiple_by_title_fallbacks_to_google(self, mock_google, mock_is_conf):
        mock_google.return_value = [
            ProviderBookData(
                title="Rebelión en la granja",
                author_name="George Orwell",
                isbn="9788499890951",
                page_count=144,
                raw_payload={
                    "id": "rebelion1984id",
                    "volumeInfo": {
                        "title": "Rebelión en la granja",
                        "authors": ["George Orwell"],
                        "pageCount": 144,
                        "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9788499890951"}],
                    },
                },
            )
        ]

        books = import_multiple_by_title("Rebelión en la granja")
        assert len(books) == 1
        assert books[0].title == "Rebelión en la granja"
        assert books[0].page_count == 144


@pytest.mark.django_db
class TestBookSerializerPageCount:
    """Verifica que BookSerializer expone y permite actualizar page_count."""

    def test_book_serializer_includes_page_count(self):
        author = Author.objects.create(name="Isaac Asimov")
        book = Book.objects.create(
            title="Fundación",
            author=author,
            page_count=256,
            isbn="9788497594257",
        )

        serializer = BookSerializer(book)
        assert "page_count" in serializer.data
        assert serializer.data["page_count"] == 256

    def test_book_serializer_updates_page_count(self):
        author = Author.objects.create(name="Isaac Asimov")
        book = Book.objects.create(
            title="Fundación e Imperio",
            author=author,
            page_count=None,
        )

        serializer = BookSerializer(book, data={"page_count": 304}, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated_book = serializer.save()
        assert updated_book.page_count == 304

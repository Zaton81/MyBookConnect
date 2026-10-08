"""
Suite de Pruebas Automatizadas para el Sprint 19: Marketplace y Enlaces Editoriales.
RoadmapV3 Sección 30 (Marketplace / Editoriales).
Verifica agregación multitienda, apoyo a librerías locales, venta directa oficial,
catálogo de editoriales y telemetría de conversión ética y anonimizada sin almacenar PII.
"""
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Book,
    Author,
    Publisher,
    BookBuyLink,
    MarketplaceClick,
    AffiliateClick,
)
from books.services.marketplace_service import MarketplaceService, ETHICAL_DISCLOSURE

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="lector_curioso",
        email="lector@example.com",
        password="Password123!",
    )


@pytest.fixture
def author_user(db):
    return User.objects.create_user(
        username="autor_verificado",
        email="autor@example.com",
        password="Password123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin_marketplace",
        email="admin@example.com",
        password="Password123!",
    )


@pytest.fixture
def author_entity(db, author_user):
    return Author.objects.create(
        name="Laura Gallego García",
        is_verified=True,
        claimed_by=author_user,
    )


@pytest.fixture
def publisher_entity(db):
    return Publisher.objects.create(
        name="Editorial Minotauro",
        description="Sello especializado en literatura fantástica y ciencia ficción.",
        website="https://www.planetadelibros.com/editorial/minotauro/16",
        country="España",
        is_verified=True,
    )


@pytest.fixture
def book_sample(db, author_entity, publisher_entity):
    return Book.objects.create(
        title="Memorias de Idhún: La Resistencia",
        author=author_entity,
        publisher=publisher_entity,
        isbn="9788467502695",
        google_volume_id="test_gvol_123",
        description="Trilogía de fantasía épica creada por Laura Gallego.",
    )


@pytest.mark.django_db
class TestSprint19MarketplaceEditoriales:
    def test_marketplace_offers_generation(self, api_client, book_sample, regular_user):
        """
        Verifica que GET /api/v1/books/<id>/marketplace/ devuelve opciones multitienda
        completas: red de librerías independientes (TodosTusLibros), grandes cadenas (Casa del Libro, Fnac),
        Amazon multiformato (con tag de asociado), Google Books y la web oficial de la editorial.
        """
        api_client.force_authenticate(user=regular_user)
        response = api_client.get(f"/api/v1/books/{book_sample.id}/marketplace/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["book_id"] == book_sample.id
        assert data["book_title"] == "Memorias de Idhún: La Resistencia"
        assert data["author_name"] == "Laura Gallego García"
        assert data["isbn"] == "9788467502695"
        assert data["can_manage"] is False  # regular_user no es propietario
        assert ETHICAL_DISCLOSURE in data["disclosure"]

        offers = data["offers"]
        merchant_names = [o["merchant_name"].lower() for o in offers]

        # Verificar presencia de comercios esenciales
        assert any("todostuslibros" in m for m in merchant_names)
        assert any("casa del libro" in m for m in merchant_names)
        assert any("fnac" in m for m in merchant_names)
        assert any("amazon" in m for m in merchant_names)
        assert any("google play" in m for m in merchant_names)
        assert any("editorial minotauro" in m for m in merchant_names)

        # Verificar agrupación por formato
        assert len(data["by_format"]["paperback"]) >= 1
        assert len(data["by_format"]["ebook"]) >= 1
        assert len(data["by_format"]["audiobook"]) >= 1

        # Verificar agrupación por tipo de comercio
        assert len(data["by_merchant_type"]["indie"]) >= 1
        assert len(data["by_merchant_type"]["online"]) >= 1
        assert len(data["by_merchant_type"]["publisher"]) >= 1

    def test_record_anonymous_marketplace_click(self, api_client, book_sample):
        """
        Verifica que POST /api/v1/books/<id>/marketplace/click/ registra un evento de
        telemetría anónima sin asociar datos del usuario, cumpliendo con el RGPD.
        Si la tienda es Amazon, comprueba que también se registra en AffiliateClick.
        """
        # Clic hacia TodosTusLibros
        resp_ttl = api_client.post(
            f"/api/v1/books/{book_sample.id}/marketplace/click/",
            {"merchant_name": "TodosTusLibros", "format": "paperback"},
            format="json",
        )
        assert resp_ttl.status_code == status.HTTP_201_CREATED
        assert resp_ttl.data["status"] == "recorded"
        assert MarketplaceClick.objects.filter(book=book_sample, merchant_name="TodosTusLibros").exists()

        # Clic hacia Amazon
        resp_amz = api_client.post(
            f"/api/v1/books/{book_sample.id}/marketplace/click/",
            {"merchant_name": "Amazon", "format": "paperback"},
            format="json",
        )
        assert resp_amz.status_code == status.HTTP_201_CREATED
        assert MarketplaceClick.objects.filter(book=book_sample, merchant_name="Amazon").exists()
        assert AffiliateClick.objects.filter(book=book_sample, format="paperback").exists()

    def test_author_owner_can_create_and_delete_official_buy_link(
        self, api_client, book_sample, author_user
    ):
        """
        Verifica que un autor autenticado que ha verificado la autoría del libro
        puede añadir un enlace oficial de compra y posteriormente eliminarlo.
        """
        api_client.force_authenticate(user=author_user)

        # 1. Crear enlace oficial
        payload = {
            "merchant_name": "Tienda Oficial de Laura Gallego",
            "merchant_type": BookBuyLink.MerchantType.PUBLISHER_DIRECT,
            "format": BookBuyLink.BookFormat.HARDCOVER,
            "url": "https://www.lauragallego.com/tienda/memorias-de-idhun-1",
            "price": "24.95",
            "currency": "EUR",
        }
        create_resp = api_client.post(
            f"/api/v1/books/{book_sample.id}/marketplace/links/",
            payload,
            format="json",
        )
        assert create_resp.status_code == status.HTTP_201_CREATED
        link_id = create_resp.data["id"]
        assert create_resp.data["is_official"] is True
        assert create_resp.data["price"] == 24.95

        # 2. Verificar que se incluye como oferta prioritaria en el marketplace
        offers_resp = api_client.get(f"/api/v1/books/{book_sample.id}/marketplace/")
        assert offers_resp.status_code == status.HTTP_200_OK
        assert offers_resp.data["can_manage"] is True  # autor_user puede gestionar
        custom_offer = next((o for o in offers_resp.data["offers"] if o["id"] == link_id), None)
        assert custom_offer is not None
        assert custom_offer["is_official"] is True

        # 3. Eliminar enlace oficial
        del_resp = api_client.delete(f"/api/v1/books/marketplace/links/{link_id}/")
        assert del_resp.status_code == status.HTTP_204_NO_CONTENT
        assert not BookBuyLink.objects.filter(pk=link_id).exists()

    def test_non_author_forbidden_from_managing_buy_links(
        self, api_client, book_sample, regular_user
    ):
        """
        Verifica que un usuario corriente no puede añadir ni manipular enlaces comerciales oficiales.
        """
        api_client.force_authenticate(user=regular_user)
        payload = {
            "merchant_name": "Tienda No Autorizada",
            "merchant_type": BookBuyLink.MerchantType.ONLINE_RETAILER,
            "format": BookBuyLink.BookFormat.PAPERBACK,
            "url": "https://spam.example.com",
            "price": "9.99",
        }
        resp = api_client.post(
            f"/api/v1/books/{book_sample.id}/marketplace/links/",
            payload,
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_publisher_catalog_and_filtering(self, api_client, publisher_entity, book_sample):
        """
        Verifica que GET /api/v1/books/publishers/ devuelve la lista de editoriales
        con conteo de publicaciones y permite filtrar por nombre o país.
        """
        # Crear otra editorial para probar filtros
        Publisher.objects.create(
            name="Editorial Anagrama",
            country="España",
            is_verified=True,
        )

        response = api_client.get("/api/v1/books/publishers/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] >= 2

        # Minotauro debe tener al menos 1 libro asociado
        minotauro = next(
            (p for p in response.data["results"] if p["slug"] == publisher_entity.slug), None
        )
        assert minotauro is not None
        assert minotauro["books_count"] == 1

        # Filtro de búsqueda
        search_resp = api_client.get("/api/v1/books/publishers/?search=Minotauro")
        assert search_resp.status_code == status.HTTP_200_OK
        assert search_resp.data["count"] == 1
        assert search_resp.data["results"][0]["name"] == "Editorial Minotauro"

    def test_publisher_detail_view(self, api_client, publisher_entity, book_sample):
        """
        Verifica que GET /api/v1/books/publishers/<slug_or_id>/ devuelve los datos
        de la editorial y su catálogo de libros publicados.
        """
        response = api_client.get(f"/api/v1/books/publishers/{publisher_entity.slug}/")
        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert data["id"] == publisher_entity.id
        assert data["name"] == "Editorial Minotauro"
        assert data["total_books"] == 1
        assert len(data["books"]) == 1
        assert data["books"][0]["id"] == book_sample.id
        assert data["books"][0]["title"] == "Memorias de Idhún: La Resistencia"

    def test_marketplace_service_validation_errors(self, book_sample, author_user):
        """
        Verifica las validaciones de datos en MarketplaceService (campos vacíos).
        """
        with pytest.raises(Exception):
            MarketplaceService.create_or_update_buy_link(
                book_id=book_sample.id,
                user=author_user,
                data={"merchant_name": "", "url": ""},
            )

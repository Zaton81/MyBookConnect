import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, ReadingStatus, Review, UserBook, normalize_title
from books.serializers import BookSerializer
from books.services.deduplication_service import (
    deduplicate_all_books,
    find_duplicate_books,
    merge_books,
)
from users.models import PrivacyChoices

User = get_user_model()


@pytest.mark.django_db
class TestCatalogDeduplicationAndNormalization:
    """Pruebas de normalización, unificación de ediciones (físico/digital) y fusión atómica."""

    def test_normalize_title_utility(self):
        t1 = "Cien años de soledad"
        t2 = "  CIEN AÑOS DE SOLEDAD.  "
        t3 = "Cien anos de soledad!"
        t4 = "El señor de los anillos: Las dos torres"

        assert normalize_title(t1) == "cien anos de soledad"
        assert normalize_title(t2) == "cien anos de soledad"
        assert normalize_title(t3) == "cien anos de soledad"
        assert normalize_title(t4) == "el senor de los anillos las dos torres"

    def test_additional_isbns_and_find_by_isbn(self):
        author = Author.objects.create(name="Ken Follett")
        book = Book.objects.create(
            title="Los pilares de la Tierra",
            author=author,
            isbn="978-84-01-02428-3",
        )

        # Añadir ISBN de edición de bolsillo / digital
        assert book.add_isbn("978-84-8346-581-3") is True
        # Intentar añadir el mismo ISBN principal debe retornar False
        assert book.add_isbn("9788401024283") is False
        # Intentar añadir el mismo ISBN secundario debe retornar False
        assert book.add_isbn("9788483465813") is False
        book.save()

        assert len(book.get_all_isbns()) == 2
        assert "9788401024283" in book.get_all_isbns()
        assert "9788483465813" in book.get_all_isbns()

        # Búsqueda por ISBN principal
        found_primary = Book.find_by_isbn("978-84-01-02428-3")
        assert found_primary is not None
        assert found_primary.id == book.id

        # Búsqueda por ISBN secundario (edición digital)
        found_secondary = Book.find_by_isbn("9788483465813")
        assert found_secondary is not None
        assert found_secondary.id == book.id

    def test_serializer_unifies_physical_and_digital_editions(self):
        author = Author.objects.create(name="Frank Herbert")

        # 1. Crear edición física con ISBN 1
        serializer1 = BookSerializer(
            data={
                "title": "Dune",
                "author_id": author.id,
                "isbn": "9788466353786",
                "description": "Edición física clásica.",
            }
        )
        assert serializer1.is_valid(), serializer1.errors
        book1 = serializer1.save()

        # 2. Intentar crear edición digital / ebook con ISBN 2
        serializer2 = BookSerializer(
            data={
                "title": "dune",
                "author_id": author.id,
                "isbn": "9788466359999",
                "description": "Edición digital enriquecida.",
            }
        )
        assert serializer2.is_valid(), serializer2.errors
        book2 = serializer2.save()

        # Deben ser el mismo registro en base de datos
        assert book1.id == book2.id
        assert Book.objects.filter(author=author).count() == 1

        book1.refresh_from_db()
        assert book1.isbn == "9788466353786"
        assert "9788466359999" in book1.additional_isbns

    def test_merge_books_transfers_userbooks_and_reviews_safely(self):
        author = Author.objects.create(name="Isabel Allende")
        book_a = Book.objects.create(
            title="La casa de los espíritus",
            author=author,
            isbn="9788401342585",
            description="Ficha principal de la obra.",
        )
        book_b = Book.objects.create(
            title="La Casa De Los Espiritus (Edición Especial)",
            author=author,
            isbn="9788439598145",
            description="Edición alternativa de bolsillo.",
        )

        user1 = User.objects.create_user(username="reader_one", email="one@test.com")
        user2 = User.objects.create_user(username="reader_two", email="two@test.com")
        user3 = User.objects.create_user(username="reader_three", email="three@test.com")

        # user1 solo tenía book_b
        UserBook.objects.create(
            user=user1, book=book_b, status=ReadingStatus.READ, rating=5
        )

        # user2 tenía ambos: book_a en want_to_read y book_b en read
        UserBook.objects.create(
            user=user2, book=book_a, status=ReadingStatus.WANT_TO_READ
        )
        UserBook.objects.create(
            user=user2, book=book_b, status=ReadingStatus.READ, rating=4
        )

        # user3 escribió reseña en book_b
        Review.objects.create(
            user=user3, book=book_b, rating=5, title="Increíble", text="Excelente libro"
        )

        # Ejecutar fusión atómica de book_b en book_a
        merged = merge_books(book_a, [book_b])

        assert merged.id == book_a.id
        assert not Book.objects.filter(id=book_b.id).exists()
        assert "9788439598145" in merged.additional_isbns

        # User1 ahora tiene book_a
        ub1 = UserBook.objects.get(user=user1)
        assert ub1.book_id == book_a.id
        assert ub1.status == ReadingStatus.READ

        # User2 tiene book_a con el estado más avanzado (READ en vez de WANT_TO_READ)
        ub2 = UserBook.objects.get(user=user2)
        assert ub2.book_id == book_a.id
        assert ub2.status == ReadingStatus.READ
        assert ub2.rating == 4

        # Reseña de user3 reasociada a book_a
        rev = Review.objects.get(user=user3)
        assert rev.book_id == book_a.id

    def test_find_and_deduplicate_all_books(self):
        author = Author.objects.create(name="Javier Moro")
        Book.objects.create(title="El imperio eres tú", author=author, isbn="111")
        Book.objects.create(title="EL IMPERIO ERES TÚ", author=author, isbn="222")

        groups = find_duplicate_books()
        assert len(groups) >= 1

        res = deduplicate_all_books()
        assert res["groups_merged"] >= 1
        assert res["duplicates_removed"] >= 1

        # Comprobar que no quedan duplicados
        remaining = find_duplicate_books()
        assert len(remaining) == 0


@pytest.mark.django_db
class TestGlobalSearchAPI:
    """Pruebas de la API de Búsqueda Global Unificada (/api/v1/search/)."""

    def setup_method(self):
        self.client = APIClient()

    def test_global_search_empty_query(self):
        response = self.client.get("/api/v1/search/?q=")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_results"] == 0
        assert data["books"] == []
        assert data["authors"] == []
        assert data["users"] == []

    def test_global_search_returns_books_authors_and_users(self):
        author = Author.objects.create(name="Albert Espinosa")
        book = Book.objects.create(
            title="Si nos enseñaran a perder, ganaríamos siempre",
            author=author,
            isbn="9788425358265",
        )
        user = User.objects.create_user(
            username="albert_reader",
            email="albert@test.com",
            first_name="Alberto",
            privacy_level=PrivacyChoices.PUBLIC,
        )

        response = self.client.get("/api/v1/search/?q=albert")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_results"] >= 3
        # Match en libro por autor Albert
        assert any(b["id"] == book.id for b in data["books"])
        # Match en autor
        assert any(a["id"] == author.id for a in data["authors"])
        # Match en usuario
        assert any(u["id"] == user.id for u in data["users"])

    def test_global_search_by_secondary_isbn(self):
        author = Author.objects.create(name="Carla Montero")
        book = Book.objects.create(
            title="El medallón de fuego",
            author=author,
            isbn="846635879X",
        )
        book.add_isbn("9788401025990")
        book.save()

        # Buscar por el ISBN secundario
        response = self.client.get("/api/v1/search/?q=9788401025990")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["books"]) == 1
        assert data["books"][0]["id"] == book.id
        assert "9788401025990" in data["books"][0]["additional_isbns"]

    def test_global_search_filter_by_type(self):
        author = Author.objects.create(name="Almudena Grandes")
        Book.objects.create(
            title="Las Edades de Lulú",
            author=author,
            isbn="8439705964",
        )
        User.objects.create_user(
            username="almudena_fan",
            email="almudena@test.com",
            privacy_level=PrivacyChoices.PUBLIC,
        )

        # Solo libros
        res_books = self.client.get("/api/v1/search/?q=almudena&type=books")
        assert res_books.status_code == status.HTTP_200_OK
        d_books = res_books.json()
        assert len(d_books["books"]) > 0
        assert len(d_books["authors"]) == 0
        assert len(d_books["users"]) == 0

        # Solo autores
        res_authors = self.client.get("/api/v1/search/?q=almudena&type=authors")
        assert res_authors.status_code == status.HTTP_200_OK
        d_authors = res_authors.json()
        assert len(d_authors["books"]) == 0
        assert len(d_authors["authors"]) > 0
        assert len(d_authors["users"]) == 0

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, FAQ
from mybookconnect.html_sanitizer import sanitize_html, sanitize_plain_text
from users.models import PrivacyChoices

User = get_user_model()


@pytest.mark.django_db
class TestSprint5QualityAndPerformance:
    """
    Suite de calidad, rendimiento y robustez para RoadmapV3 Sprint 5.
    Cubre:
    - Control de queries SQL y erradicación de consultas N+1 en búsqueda y catálogo.
    - Sanitización defensiva contra XSS y HTML malicioso en UGC.
    - Rendimiento y filtros del endpoint público de FAQs.
    - Contratos de respuesta unificados para libros (físico/digital).
    """

    def setup_method(self):
        self.client = APIClient()

    def test_sanitize_plain_text_resilience(self):
        """Verifica que sanitize_plain_text neutralice cualquier payload XSS y retire etiquetas HTML."""
        malicious_inputs = [
            ("<script>alert('xss')</script>", ""),
            ("<img src=x onerror=alert(1)>", ""),
            ("<a href='javascript:void(0)'>Hacking</a>", "Hacking"),
            ("<p>Texto normal <b>en negrita</b></p>", "Texto normal en negrita"),
            ("<div><span>Subtexto</span><iframe src='http://evil.com'></iframe></div>", "Subtexto"),
            ("Sin etiquetas HTML normales", "Sin etiquetas HTML normales"),
        ]

        for raw, expected in malicious_inputs:
            sanitized = sanitize_plain_text(raw)
            assert "<script" not in sanitized
            assert "<img" not in sanitized
            assert "<iframe" not in sanitized
            assert "onerror" not in sanitized
            assert sanitized == expected

    def test_sanitize_html_resilience(self):
        """Verifica que sanitize_html conserve únicamente marcado seguro y neutralice scripts."""
        raw_html = (
            "<p>Este es un texto <strong>muy importante</strong> con un enlace "
            "<a href='https://example.com' onclick='stealCookies()'>enlace seguro</a> "
            "<script>alert('pwned')</script><iframe src='https://malicious.org'></iframe></p>"
        )

        clean = sanitize_html(raw_html)

        # Debe conservar etiquetas permitidas
        assert "<strong>muy importante</strong>" in clean
        assert "<p>" in clean
        assert "https://example.com" in clean
        assert 'rel="noopener noreferrer nofollow"' in clean

        # Debe erradicar scripts, iframes y handlers
        assert "<script" not in clean
        assert "alert(" not in clean
        assert "<iframe" not in clean
        assert "onclick" not in clean
        assert "stealCookies" not in clean

    def test_global_search_n_plus_one_eradication(self, django_assert_max_num_queries):
        """
        Verifica que la búsqueda global no genere N+1 queries independientemente
        de la cantidad de libros y autores devueltos.
        """
        author1 = Author.objects.create(name="Gabriel García Márquez")
        author2 = Author.objects.create(name="Mario Vargas Llosa")
        cat1 = Category.objects.create(name="Realismo Mágico", slug="realismo-magico")
        cat2 = Category.objects.create(name="Novela", slug="novela")

        # Crear 6 libros con autores y categorías
        books = []
        for i in range(6):
            b = Book.objects.create(
                title=f"Crónica literaria volumen {i + 1}",
                author=author1 if i % 2 == 0 else author2,
                isbn=f"97884000000{i:02d}",
                description="Una novela clásica sobre el destino y la memoria.",
            )
            b.categories.add(cat1, cat2)
            books.append(b)

        # Crear usuarios para el test
        user1 = User.objects.create_user(
            username="cronica_reader_1",
            email="cronica1@example.com",
            password="TestPassword123!",
            privacy_level=PrivacyChoices.PUBLIC,
        )
        user2 = User.objects.create_user(
            username="cronica_reader_2",
            email="cronica2@example.com",
            password="TestPassword123!",
            privacy_level=PrivacyChoices.PUBLIC,
        )

        # Búsqueda con límite de resultados
        # Con prefetch_related('categories', 'authors') y select_related('author'),
        # el número de consultas debe estar estrictamente acotado y no crecer linealmente con N libros.
        with django_assert_max_num_queries(10):
            response = self.client.get("/api/v1/search/?q=literaria&type=all")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["total_results"] >= 6
        assert len(data["books"]) >= 6
        # Validar estructura y prefetching resuelto
        for b_data in data["books"]:
            assert "title" in b_data
            assert "author" in b_data
            assert b_data["author"] is not None

    def test_public_faqs_ordering_and_filtering(self):
        """
        Verifica que el endpoint de FAQs (/api/v1/faqs/) respete el ordenamiento,
        excluya elementos no publicados y filtre adecuadamente por categoría.
        """
        # Crear FAQs con diversos estados y órdenes
        FAQ.objects.create(
            question="¿Segunda pregunta?",
            answer="Respuesta 2",
            category="general",
            order=2,
            is_published=True,
        )
        FAQ.objects.create(
            question="¿Primera pregunta?",
            answer="Respuesta 1",
            category="general",
            order=1,
            is_published=True,
        )
        FAQ.objects.create(
            question="¿Pregunta de autores?",
            answer="Respuesta autores",
            category="authors",
            order=1,
            is_published=True,
        )
        FAQ.objects.create(
            question="¿Pregunta oculta / borrador?",
            answer="No visible",
            category="general",
            order=0,
            is_published=False,
        )

        # 1. Consulta sin filtros: debe traer las 3 publicadas en orden ascendente
        res_all = self.client.get("/api/v1/faqs/")
        assert res_all.status_code == status.HTTP_200_OK
        faqs = res_all.data if isinstance(res_all.data, list) else res_all.data.get("results", [])
        assert len(faqs) == 3

        # Las preguntas no publicadas no deben aparecer
        questions = [f["question"] for f in faqs]
        assert "¿Pregunta oculta / borrador?" not in questions

        # La primera debe tener menor 'order' que la segunda
        general_faqs = [f for f in faqs if f["category"] == "general"]
        assert general_faqs[0]["question"] == "¿Primera pregunta?"
        assert general_faqs[1]["question"] == "¿Segunda pregunta?"

        # 2. Filtrado por categoría 'authors'
        res_authors = self.client.get("/api/v1/faqs/?category=authors")
        assert res_authors.status_code == status.HTTP_200_OK
        authors_faqs = res_authors.data if isinstance(res_authors.data, list) else res_authors.data.get("results", [])
        assert len(authors_faqs) == 1
        assert authors_faqs[0]["question"] == "¿Pregunta de autores?"

    def test_search_unified_editions_contract(self):
        """
        Verifica que libros con ediciones físicas y digitales unificadas
        devuelvan el contrato completo con 'additional_isbns' e información agregada.
        """
        author = Author.objects.create(name="Carlos Ruiz Zafón")
        book = Book.objects.create(
            title="La sombra del viento",
            author=author,
            isbn="9788408043645",
            description="El misterio del cementerio de los libros olvidados.",
        )
        book.add_isbn("9788408163435")  # Edición digital / eBook
        book.add_isbn("9788408079545")  # Edición de bolsillo
        book.save()

        # Búsqueda por ISBN secundario (edición digital)
        response = self.client.get("/api/v1/search/?q=9788408163435&type=books")
        assert response.status_code == status.HTTP_200_OK
        results = response.data.get("books", [])
        assert len(results) == 1
        found_book = results[0]

        assert found_book["id"] == book.id
        assert found_book["title"] == "La sombra del viento"
        assert found_book["isbn"] == "9788408043645"
        assert "9788408163435" in found_book.get("additional_isbns", [])
        assert "9788408079545" in found_book.get("additional_isbns", [])

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from ai.services import (
    compare_books_ai,
    explain_book_ai,
    get_book_ai_summary,
)
from books.models import Author, Book, Category, Review, UserBook

User = get_user_model()


@pytest.mark.django_db
class TestPhase24ProductAI:
    def setup_method(self):
        self.user = User.objects.create_user(
            username='lector_fase24', email='fase24@test.com', password='password123'
        )
        self.author_a = Author.objects.create(name='Gabriel García Márquez')
        self.author_b = Author.objects.create(name='Isabel Allende')

        self.category = Category.objects.create(
            name='Realismo Mágico', slug='realismo-magico'
        )

        self.book_a = Book.objects.create(
            title='Cien años de soledad',
            author=self.author_a,
            description='La saga de la familia Buendía en el pueblo ficticio de Macondo.',
            average_rating=4.8,
        )
        self.book_a.categories.add(self.category)

        self.book_b = Book.objects.create(
            title='La casa de los espíritus',
            author=self.author_b,
            description='Crónica familiar de los Trueba a lo largo de cuatro generaciones.',
            average_rating=4.5,
        )
        self.book_b.categories.add(self.category)

        self.client = APIClient()

    # ─── 1. Explicación de libros (Contexto histórico, claves temáticas) ───

    def test_explain_book_ai_success(self):
        """Verifica la generación de explicación estructurada con IA y marcado transparente."""
        mock_response = {
            "success": True,
            "content": (
                "### 🏛️ Contexto Histórico y de Creación\nPublicada en 1967...\n\n"
                "### 🔑 Claves Temáticas Fundamentales\n- La soledad y el tiempo circular.\n\n"
                "### 🖋️ Estilo Narrativo y Voz del Autor\nProsa barroca y poética.\n\n"
                "### 💡 Guía de Lectura y A Quién se Recomienda\nImprescindible para amantes del realismo mágico."
            ),
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_tokens": 120,
            "completion_tokens": 90,
            "duration_ms": 300,
        }

        with patch("ai.services.get_ai_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.name = "openai"
            mock_provider.model_chat = "gpt-4o-mini"
            mock_provider.chat_completion.return_value = mock_response
            mock_get_provider.return_value = mock_provider

            result = explain_book_ai(book=self.book_a, user=self.user)

            assert result["is_ai_generated"] is True
            assert "✨ Generado por IA" in result["badge"]
            assert "fines orientativos" in result["disclaimer"]
            assert "Contexto Histórico" in result["explanation"]
            assert result["book_id"] == self.book_a.id

    def test_explain_book_ai_fallback_offline(self):
        """Si el LLM no está disponible, genera una explicación determinista sin romper."""
        with patch("ai.services.get_ai_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.name = "rule-based"
            mock_provider.model_chat = "rule-based"
            mock_provider.chat_completion.return_value = {"success": False, "error": "Provider offline"}
            mock_get_provider.return_value = mock_provider

            result = explain_book_ai(book=self.book_a, user=self.user)

            assert result["is_ai_generated"] is True
            assert result["ai_online"] is False
            assert "Contexto Histórico" in result["explanation"]
            assert "Realismo Mágico" in result["explanation"]

    def test_explain_book_api_endpoint(self):
        """Verifica el endpoint POST /api/v1/books/<pk>/ai/explain/."""
        self.client.force_authenticate(user=self.user)

        with patch("books.ai_views.explain_book_ai") as mock_explain:
            mock_explain.return_value = {
                "book_id": self.book_a.id,
                "book_title": self.book_a.title,
                "explanation": "Explicación analítica mock...",
                "ai_online": True,
                "provider": "ollama",
                "is_ai_generated": True,
                "badge": "✨ Generado por IA",
                "disclaimer": "✨ Contenido generado por Inteligencia Artificial con fines orientativos y divulgativos.",
            }

            url = f"/api/v1/books/{self.book_a.id}/ai/explain/"
            response = self.client.post(url)

            assert response.status_code == 200
            data = response.json()
            assert data["is_ai_generated"] is True
            assert data["badge"] == "✨ Generado por IA"
            assert "disclaimer" in data

    def test_explain_book_api_requires_auth(self):
        """El endpoint de explicación requiere autenticación."""
        url = f"/api/v1/books/{self.book_a.id}/ai/explain/"
        response = self.client.post(url)
        assert response.status_code == 401

    # ─── 2. Comparativas temáticas entre obras ───

    def test_compare_books_ai_success(self):
        """Verifica la comparación analítica entre dos obras literarias."""
        mock_response = {
            "success": True,
            "content": (
                "### 🔗 Puntos de Convergencia\nAmbas obras abordan sagas familiares en América Latina...\n\n"
                "### ⚡ Contrastes y Enfoques Distintivos\nGarcía Márquez profundiza en lo mítico; Allende en lo político.\n\n"
                "### 🧭 Cuál Leer Primero y Experiencia Lectora\nComenzar por Cien años de soledad."
            ),
            "provider": "openai",
            "model": "gpt-4o-mini",
            "prompt_tokens": 180,
            "completion_tokens": 120,
            "duration_ms": 400,
        }

        with patch("ai.services.get_ai_provider") as mock_get_provider:
            mock_provider = MagicMock()
            mock_provider.name = "openai"
            mock_provider.model_chat = "gpt-4o-mini"
            mock_provider.chat_completion.return_value = mock_response
            mock_get_provider.return_value = mock_provider

            result = compare_books_ai(book_a=self.book_a, book_b=self.book_b, user=self.user)

            assert result["is_ai_generated"] is True
            assert "✨ Generado por IA" in result["badge"]
            assert "Puntos de Convergencia" in result["comparison"]
            assert result["book_a"]["id"] == self.book_a.id
            assert result["book_b"]["id"] == self.book_b.id

    def test_compare_books_api_endpoint(self):
        """Verifica el endpoint POST /api/v1/books/ai/compare/."""
        self.client.force_authenticate(user=self.user)

        with patch("books.ai_views.compare_books_ai") as mock_compare:
            mock_compare.return_value = {
                "book_a": {"id": self.book_a.id, "title": self.book_a.title},
                "book_b": {"id": self.book_b.id, "title": self.book_b.title},
                "comparison": "Comparativa mock...",
                "ai_online": True,
                "provider": "openai",
                "is_ai_generated": True,
                "badge": "✨ Generado por IA",
                "disclaimer": "✨ Contenido generado por Inteligencia Artificial con fines orientativos y divulgativos.",
            }

            url = "/api/v1/books/ai/compare/"
            response = self.client.post(
                url,
                {"book_a_id": self.book_a.id, "book_b_id": self.book_b.id},
                format="json",
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_ai_generated"] is True
            assert data["book_a"]["id"] == self.book_a.id

    def test_compare_books_api_validation(self):
        """Valida que no se permita comparar el mismo libro o campos vacíos."""
        self.client.force_authenticate(user=self.user)
        url = "/api/v1/books/ai/compare/"

        # Mismo libro
        res_same = self.client.post(
            url,
            {"book_a_id": self.book_a.id, "book_b_id": self.book_a.id},
            format="json",
        )
        assert res_same.status_code == 400

        # Campos faltantes
        res_missing = self.client.post(
            url,
            {"book_a_id": self.book_a.id},
            format="json",
        )
        assert res_missing.status_code == 400

    # ─── 3. Resúmenes estructurados con disclaimer obligatorio ───

    def test_book_summary_includes_ai_label_and_disclaimer(self):
        """Verifica que el resumen generado por IA incluya etiqueta y disclaimer explícito."""
        result = get_book_ai_summary(book=self.book_a)
        assert result["is_ai_generated"] is True
        assert "✨ Generado por IA" in result["badge"]
        assert "disclaimer" in result

    # ─── 4. Unificación de notas a escala 1-5 estrellas ───

    def test_unified_ratings_range_one_to_five(self):
        """Asegura que el modelo no admita notas mayores a 5 estrellas tanto en UserBook como en Review."""
        from django.core.exceptions import ValidationError

        # UserBook rating válido 1-5
        ub = UserBook(user=self.user, book=self.book_a, rating=5)
        ub.full_clean()  # Válido

        ub_invalid = UserBook(user=self.user, book=self.book_a, rating=10)
        with pytest.raises(ValidationError):
            ub_invalid.full_clean()

        # Review rating válido 1-5
        rev = Review(user=self.user, book=self.book_a, rating=5, text="Excelente")
        rev.full_clean()  # Válido

        rev_invalid = Review(user=self.user, book=self.book_a, rating=10, text="Excelente")
        with pytest.raises(ValidationError):
            rev_invalid.full_clean()

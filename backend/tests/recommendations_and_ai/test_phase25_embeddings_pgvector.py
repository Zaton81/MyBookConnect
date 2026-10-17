from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, BookEmbedding, Category, EmbeddingStatus
from books.services.embedding_service import (
    compute_book_content_hash,
    generate_book_embedding,
    get_embedding_catalog_stats,
    normalize_book_content_for_embedding,
    search_books_by_embedding,
)
from books.tasks import batch_reindex_embeddings_task, generate_book_embedding_task

User = get_user_model()


@pytest.mark.django_db
class TestPhase25EmbeddingsPgvector:
    def setup_method(self):
        self.user = User.objects.create_user(
            username='lector_fase25', email='fase25@test.com', password='password123'
        )
        self.author = Author.objects.create(name='Julio Cortázar')
        self.category = Category.objects.create(name='Realismo Fantástico', slug='realismo-fantastico')

        self.book = Book.objects.create(
            title='Rayuela',
            author=self.author,
            description='<p>Una contranovela <b>innovadora</b> que propone múltiples itinerarios de lectura.</p>',
            average_rating=4.7,
        )
        self.book.categories.add(self.category)
        self.client = APIClient()

    # ─── 1. Normalización de Contenido y Hashing Idempotente ───

    def test_content_normalization_and_hash(self):
        """Verifica la normalización semántica, eliminación de HTML y determinismo del hash SHA256."""
        norm_text, hash_val = normalize_book_content_for_embedding(self.book)

        assert "<p>" not in norm_text
        assert "<b>" not in norm_text
        assert "innovadora" in norm_text
        assert "Título: Rayuela." in norm_text
        assert "Autor: Julio Cortázar." in norm_text
        assert "Géneros: Realismo Fantástico." in norm_text
        assert len(hash_val) == 64

        # Idempotencia: el mismo libro genera idéntico hash
        assert compute_book_content_hash(self.book) == hash_val

    def test_content_hash_changes_on_update(self):
        """Si el título o sinopsis cambian, el hash SHA256 varía para invalidar el vector (STALE)."""
        initial_hash = compute_book_content_hash(self.book)

        self.book.description = 'Nueva sinopsis actualizada sin etiquetas.'
        self.book.save()

        updated_hash = compute_book_content_hash(self.book)
        assert initial_hash != updated_hash

    # ─── 2. Generación y Persistencia de Embeddings ───

    def test_generate_book_embedding_success(self):
        """Verifica la generación y persistencia del vector en BookEmbedding satélite."""
        mock_vector = [0.12, -0.45, 0.78, 0.05]

        with patch("books.services.embedding_service.get_embedding_for_text", return_value=mock_vector):
            rec = generate_book_embedding(self.book)

            assert rec.embedding_status == EmbeddingStatus.COMPLETED
            assert rec.dimension == 4
            assert rec.vector == mock_vector
            assert rec.embedding_model == "nomic-embed-text"
            assert rec.embedded_at is not None
            assert rec.book == self.book

    def test_generate_book_embedding_idempotence(self):
        """Si no hay cambios de contenido ni de modelo, no vuelve a consumir el proveedor de IA."""
        mock_vector = [0.1, 0.2, 0.3]

        with patch("books.services.embedding_service.get_embedding_for_text", return_value=mock_vector) as mock_get:
            # Primera llamada: genera
            rec1 = generate_book_embedding(self.book)
            assert mock_get.call_count == 1

            # Segunda llamada sin force: reutiliza registro completado
            rec2 = generate_book_embedding(self.book, force=False)
            assert mock_get.call_count == 1
            assert rec1.id == rec2.id

    def test_generate_book_embedding_failure_handling(self):
        """Si el proveedor devuelve None, el registro transiciona a FAILED sin lanzar excepción no controlada."""
        with patch("books.services.embedding_service.get_embedding_for_text", return_value=None):
            rec = generate_book_embedding(self.book, force=True)
            assert rec.embedding_status == EmbeddingStatus.FAILED

    # ─── 3. Regla de Oro: No Mezclar Modelos Incompatibles ───

    def test_search_books_by_embedding_prevents_incompatible_models_or_dimensions(self):
        """
        Garantiza que la búsqueda vectorial aísle estrictamente modelos y longitudes vectoriales.
        No debe comparar vectores de dimensiones o modelos dispares.
        """
        # Libro 1: nomic-embed-text con 3 dimensiones
        BookEmbedding.objects.create(
            book=self.book,
            vector=[1.0, 0.0, 0.0],
            dimension=3,
            embedding_model="nomic-embed-text",
            embedding_status=EmbeddingStatus.COMPLETED,
        )

        # Libro 2: modelo diferente (openai text-embedding-3-small) con 4 dimensiones
        book_b = Book.objects.create(title='Bestiario', author=self.author)
        BookEmbedding.objects.create(
            book=book_b,
            vector=[1.0, 0.0, 0.0, 0.0],
            dimension=4,
            embedding_model="text-embedding-3-small",
            embedding_status=EmbeddingStatus.COMPLETED,
        )

        query_vector = [1.0, 0.0, 0.0]  # Dimensión 3 para nomic-embed-text
        results = search_books_by_embedding(
            query_vector=query_vector,
            limit=10,
            model_name="nomic-embed-text",
        )

        # Solo debe coincidir el libro con el mismo modelo y dimensión
        assert len(results) == 1
        assert results[0][0].id == self.book.id
        assert book_b.id not in [r[0].id for r in results]

    # ─── 4. Tareas en Segundo Plano (Celery Jobs) ───

    def test_celery_generate_book_embedding_task(self):
        """Verifica la ejecución de la tarea Celery generate_book_embedding_task."""
        with patch("books.services.embedding_service.get_embedding_for_text", return_value=[0.1, 0.2]):
            success = generate_book_embedding_task(self.book.id)
            assert success is True

            rec = BookEmbedding.objects.get(book=self.book)
            assert rec.embedding_status == EmbeddingStatus.COMPLETED

    def test_celery_batch_reindex_embeddings_task(self):
        """Verifica la ejecución por lotes batch_reindex_embeddings_task."""
        with patch("books.services.embedding_service.get_embedding_for_text", return_value=[0.5, 0.5]):
            stats = batch_reindex_embeddings_task(batch_size=10, force=True)
            assert stats["candidates"] >= 1
            assert stats["indexed"] >= 1

    # ─── 5. Endpoints de API y Observabilidad ───

    def test_api_embedding_stats_endpoint(self):
        """Verifica el endpoint GET /api/v1/books/ai/embeddings/stats/."""
        self.client.force_authenticate(user=self.user)

        BookEmbedding.objects.create(
            book=self.book,
            vector=[0.1, 0.2],
            dimension=2,
            embedding_model="nomic-embed-text",
            embedding_status=EmbeddingStatus.COMPLETED,
        )

        url = "/api/v1/books/ai/embeddings/stats/"
        res = self.client.get(url)

        assert res.status_code == 200
        data = res.json()
        assert "total_books" in data
        assert "coverage_percentage" in data
        assert data["completed"] >= 1
        assert len(data["models_breakdown"]) >= 1

    def test_api_generate_book_embedding_endpoint(self):
        """Verifica el endpoint POST /api/v1/books/<pk>/ai/embeddings/generate/."""
        self.client.force_authenticate(user=self.user)

        with patch("books.services.embedding_service.get_embedding_for_text", return_value=[0.3, 0.4, 0.5]):
            url = f"/api/v1/books/{self.book.id}/ai/embeddings/generate/"

            # Modo síncrono
            res_sync = self.client.post(url, {"force": True}, format="json")
            assert res_sync.status_code == 200
            assert res_sync.json()["status"] == "completed"
            assert res_sync.json()["dimension"] == 3

            # Modo asíncrono (Celery)
            with patch("books.tasks.generate_book_embedding_task.delay") as mock_delay:
                res_async = self.client.post(url, {"async_mode": True}, format="json")
                assert res_async.status_code == 202
                assert res_async.json()["status"] == "enqueued"
                mock_delay.assert_called_once()

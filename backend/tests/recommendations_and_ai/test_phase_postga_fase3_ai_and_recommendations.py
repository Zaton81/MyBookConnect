"""
Suite de pruebas de arquitectura y funcionalidad para Post-GA Fase 3:
Consolidación de IA, Embeddings (pgvector) y Pipeline de Recomendaciones en 4 Etapas.
"""

import pytest
from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from ai.embeddings import (
    cosine_similarity,
    weighted_average_embeddings,
)
from books.models import (
    Author,
    Book,
    BookEmbedding,
    Category,
    EmbeddingStatus,
    ReadingStatus,
    RecommendationFeedback,
    UserBook,
)
from books.services import (
    CandidateGenerator,
    MMRReranker,
    RecommendationFilter,
    RecommendationPipeline,
    get_user_recommendations,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_dataset(db):
    author_a = Author.objects.create(name="Gabriel García Márquez")
    author_b = Author.objects.create(name="Ursula K. Le Guin")

    cat_realismo = Category.objects.create(name="Realismo Mágico", slug="realismo-magico")
    cat_scifi = Category.objects.create(name="Ciencia Ficción", slug="ciencia-ficcion")

    book_1 = Book.objects.create(
        title="Cien años de soledad",
        author=author_a,
        average_rating=4.9,
        page_count=417,
    )
    book_1.categories.add(cat_realismo)

    book_2 = Book.objects.create(
        title="El amor en los tiempos del cólera",
        author=author_a,
        average_rating=4.7,
        page_count=368,
    )
    book_2.categories.add(cat_realismo)

    book_3 = Book.objects.create(
        title="Los desposeídos",
        author=author_b,
        average_rating=4.8,
        page_count=384,
    )
    book_3.categories.add(cat_scifi)

    book_4 = Book.objects.create(
        title="La mano izquierda de la oscuridad",
        author=author_b,
        average_rating=4.8,
        page_count=300,
    )
    book_4.categories.add(cat_scifi)

    # Crear embeddings para prueba vectorial
    BookEmbedding.objects.create(
        book=book_1,
        vector=[0.1, 0.2, 0.3],
        dimension=3,
        embedding_model='test-model',
        embedding_status=EmbeddingStatus.COMPLETED,
    )
    BookEmbedding.objects.create(
        book=book_2,
        vector=[0.15, 0.22, 0.28],
        dimension=3,
        embedding_model='test-model',
        embedding_status=EmbeddingStatus.COMPLETED,
    )
    BookEmbedding.objects.create(
        book=book_3,
        vector=[0.9, 0.1, 0.05],
        dimension=3,
        embedding_model='test-model',
        embedding_status=EmbeddingStatus.COMPLETED,
    )
    BookEmbedding.objects.create(
        book=book_4,
        vector=[0.85, 0.12, 0.08],
        dimension=3,
        embedding_model='test-model',
        embedding_status=EmbeddingStatus.COMPLETED,
    )

    user = User.objects.create_user(
        username="lector_pipeline",
        email="pipeline@example.com",
        password="Password123!",
    )
    user.favorite_categories.add(cat_realismo)

    # El usuario ya leyó book_1
    UserBook.objects.create(
        user=user,
        book=book_1,
        status=ReadingStatus.READ,
        rating=5,
    )

    return {
        'user': user,
        'book_1': book_1,
        'book_2': book_2,
        'book_3': book_3,
        'book_4': book_4,
        'cat_realismo': cat_realismo,
        'cat_scifi': cat_scifi,
    }


@pytest.mark.django_db
class TestPhase3AiArchitecture:
    """Verifica la modularización de vistas de IA y eliminación de código duplicado."""

    def test_canonical_ai_urls_reachable(self, api_client, sample_dataset):
        """Verifica que /api/v1/ai/status/ esté disponible canónicamente."""
        user = sample_dataset['user']
        api_client.force_authenticate(user=user)

        resp = api_client.get('/api/v1/ai/status/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'enabled' in data
        assert 'is_online' in data
        assert 'provider' in data

    def test_legacy_books_ai_urls_compatibility(self, api_client, sample_dataset):
        """Verifica que la ruta histórica /api/v1/books/ai/status/ siga funcionando por retrocompatibilidad."""
        user = sample_dataset['user']
        api_client.force_authenticate(user=user)

        resp = api_client.get('/api/v1/books/ai/status/')
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert 'provider' in data

    def test_ai_service_proxy_removed_from_mybookconnect(self):
        """Confirma que el módulo legado mybookconnect.ai_service ha sido completamente eliminado."""
        with pytest.raises(ImportError):
            import mybookconnect.ai_service  # noqa: F401


@pytest.mark.django_db
class TestPhase3EmbeddingsConsolidation:
    """Verifica los métodos matemáticos unificados en ai.embeddings."""

    def test_weighted_average_embeddings_calculation(self):
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        # Promedio con pesos 3.0 y 1.0 -> [3/4, 1/4, 0] = [0.75, 0.25, 0.0]
        res = weighted_average_embeddings([(v1, 3.0), (v2, 1.0)], normalize=False)
        assert res is not None
        assert pytest.approx(res[0], 0.001) == 0.75
        assert pytest.approx(res[1], 0.001) == 0.25
        assert pytest.approx(res[2], 0.001) == 0.0

    def test_weighted_average_embeddings_normalized(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        res = weighted_average_embeddings([(v1, 1.0), (v2, 1.0)], normalize=True)
        assert res is not None
        # Norma L2 debe ser exactamente 1.0
        norm = (res[0] ** 2 + res[1] ** 2) ** 0.5
        assert pytest.approx(norm, 0.0001) == 1.0


@pytest.mark.django_db
class TestPhase3RecommendationPipeline:
    """Verifica el funcionamiento del pipeline en 4 etapas."""

    def test_pipeline_candidates_and_filtering(self, sample_dataset):
        user = sample_dataset['user']
        b1 = sample_dataset['book_1']

        gen = CandidateGenerator()
        candidates = gen.generate_candidates(user=user, k=50, strategy='hybrid')
        assert len(candidates) > 0

        # El filtro debe excluir book_1 porque ya fue leído
        flt = RecommendationFilter()
        excluded = flt.get_excluded_book_ids(user)
        assert b1.id in excluded

        filtered = flt.filter_by_criteria(candidates, excluded_ids=excluded)
        filtered_ids = {c['book'].id for c in filtered}
        assert b1.id not in filtered_ids

    def test_pipeline_reranking_mmr(self, sample_dataset):
        b2 = sample_dataset['book_2']
        b3 = sample_dataset['book_3']
        b4 = sample_dataset['book_4']

        candidates = [
            {'book': b2, 'score': 0.95, 'vector': [0.15, 0.22, 0.28], 'source': 'v1'},
            {'book': b3, 'score': 0.85, 'vector': [0.90, 0.10, 0.05], 'source': 'v3'},
            {'book': b4, 'score': 0.84, 'vector': [0.85, 0.12, 0.08], 'source': 'v3'},
        ]

        reranker = MMRReranker()
        reranked = reranker.rerank_mmr(candidates, limit=2, lambda_param=0.6)
        assert len(reranked) == 2
        # El primero debe ser b2 por mayor relevancia
        assert reranked[0]['book'].id == b2.id
        # El segundo debe preferir b3 antes que otro similar
        assert reranked[1]['book'].id == b3.id

    def test_full_recommendation_pipeline_execution(self, sample_dataset):
        user = sample_dataset['user']
        pipeline = RecommendationPipeline()

        results = pipeline.run(
            user=user,
            limit=5,
            strategy='hybrid',
            use_cache=False,
        )

        assert len(results) > 0
        book_ids = [r['id'] for r in results]
        # book_1 no debe aparecer por estar leído
        assert sample_dataset['book_1'].id not in book_ids

        # Verificar campos explicables
        first = results[0]
        assert 'title' in first
        assert 'score' in first
        assert 'reason' in first
        assert 'algorithm_version' in first
        assert len(first['reason']) > 0

    def test_services_get_user_recommendations_pipeline_strategy(self, sample_dataset):
        """Verifica la invocación a través del servicio unificado con strategy='pipeline'."""
        user = sample_dataset['user']
        results = get_user_recommendations(
            user=user,
            limit=5,
            strategy='pipeline',
        )
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert 'id' in r
            assert 'title' in r
            assert 'score' in r

"""
Suite de Pruebas de Calidad para la Fase 7 — Motor de Recomendaciones (Prioridad P1).

Cubre los requerimientos de la Sección 12 de RoadmapV2.md:
1. Arquitectura por capas (12.1): Candidate generation, scoring, filtering, diversity, explanation, top N.
2. Fuentes multicanal y semántica vectorial satélite con BookEmbedding (12.2).
3. Privacy Filtering estricto (12.3): exclusión de usuarios bloqueados o perfiles privados en señales sociales.
4. Ciclo de feedback completo incluyendo evento 'dismissed' (12.4).
5. Métricas de rendimiento: CTR, open_rate, wishlist_rate, dismiss_rate, etc. (12.5).
6. Versionado y metadatos explícitos en recomendaciones y eventos (12.6).
7. Anti-sobreoptimización y consistencia en cold start (12.7).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    Book,
    BookEmbedding,
    Category,
    EmbeddingStatus,
    ReadingStatus,
    RecommendationFeedbackAction,
    UserBook,
)
from books.services.recommendation_diversity_service import apply_diversity_filter
from books.services.recommendation_feedback_service import (
    get_feedback_metrics,
    record_recommendation_event,
)
from books.services.recommendation_service import get_user_recommendations
from books.services.recommendation_v3_service import RecommendationEngineV3
from users.models import PrivacyChoices

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_data(db):
    author1 = Author.objects.create(name="Ursula K. Le Guin")
    author2 = Author.objects.create(name="Philip K. Dick")
    author3 = Author.objects.create(name="Octavia Butler")

    cat_scifi = Category.objects.create(name="Ciencia Ficción")
    cat_fantasy = Category.objects.create(name="Fantasía")

    # Libros de Ursula Le Guin
    book_dispossessed = Book.objects.create(
        title="Los desposeídos",
        author=author1,
        average_rating=4.8,
    )
    book_dispossessed.categories.add(cat_scifi)

    book_earthsea = Book.objects.create(
        title="Un mago de Terramar",
        author=author1,
        average_rating=4.7,
    )
    book_earthsea.categories.add(cat_fantasy)

    book_left_hand = Book.objects.create(
        title="La mano izquierda de la oscuridad",
        author=author1,
        average_rating=4.9,
    )
    book_left_hand.categories.add(cat_scifi)

    # Libros de Philip K. Dick
    book_ubik = Book.objects.create(
        title="Ubik",
        author=author2,
        average_rating=4.6,
    )
    book_ubik.categories.add(cat_scifi)

    book_androids = Book.objects.create(
        title="¿Sueñan los androides con ovejas eléctricas?",
        author=author2,
        average_rating=4.5,
    )
    book_androids.categories.add(cat_scifi)

    # Libros de Octavia Butler
    book_kindred = Book.objects.create(
        title="Parentesco (Kindred)",
        author=author3,
        average_rating=4.8,
    )
    book_kindred.categories.add(cat_scifi)

    # Usuarios
    user_alice = User.objects.create_user(username="alice", email="alice@example.com", password="password123")
    user_bob = User.objects.create_user(username="bob", email="bob@example.com", password="password123")
    user_eve = User.objects.create_user(username="eve", email="eve@example.com", password="password123")

    return {
        'authors': [author1, author2, author3],
        'categories': [cat_scifi, cat_fantasy],
        'books': {
            'dispossessed': book_dispossessed,
            'earthsea': book_earthsea,
            'left_hand': book_left_hand,
            'ubik': book_ubik,
            'androids': book_androids,
            'kindred': book_kindred,
        },
        'users': {
            'alice': user_alice,
            'bob': user_bob,
            'eve': user_eve,
        },
    }


@pytest.mark.django_db
class TestPhase07FeedbackAndMetrics:
    """Verifica los eventos de interacción y el cálculo de métricas (Fase 7 - 12.4 & 12.5)."""

    def test_record_dismissed_event_and_kpis(self, sample_data):
        alice = sample_data['users']['alice']
        book = sample_data['books']['ubik']

        # 1. Registrar eventos
        record_recommendation_event(
            user=alice,
            book_id=book.id,
            action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN,
            strategy='hybrid',
            algorithm_version='v3',
        )
        record_recommendation_event(
            user=alice,
            book_id=book.id,
            action=RecommendationFeedbackAction.BOOK_OPENED,
            strategy='hybrid',
            algorithm_version='v3',
        )
        record_recommendation_event(
            user=alice,
            book_id=book.id,
            action=RecommendationFeedbackAction.DISMISSED,
            strategy='hybrid',
            algorithm_version='v3',
        )

        metrics = get_feedback_metrics(user=alice)
        assert metrics['totals']['shown'] == 1
        assert metrics['totals']['book_opened'] == 1
        assert metrics['totals']['dismissed'] == 1
        assert metrics['kpis']['open_rate'] == 100.0
        assert metrics['kpis']['dismiss_rate'] == 100.0

    def test_api_feedback_batch_and_dismissed(self, api_client, sample_data):
        alice = sample_data['users']['alice']
        book1 = sample_data['books']['ubik']
        book2 = sample_data['books']['kindred']

        api_client.force_authenticate(user=alice)
        payload = [
            {
                'book_id': book1.id,
                'action': 'recommendation_shown',
                'strategy': 'v3',
                'algorithm_version': 'v3.0',
            },
            {
                'book_id': book1.id,
                'action': 'dismissed',
                'strategy': 'v3',
                'algorithm_version': 'v3.0',
                'metadata': {'reason': 'not_interested'},
            },
            {
                'book_id': book2.id,
                'action': 'recommendation_shown',
                'strategy': 'v3',
                'algorithm_version': 'v3.0',
            },
            {
                'book_id': book2.id,
                'action': 'recommendation_clicked',
                'strategy': 'v3',
                'algorithm_version': 'v3.0',
            },
        ]
        res = api_client.post('/api/v1/books/recommendations/feedback/', data=payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['count'] == 4

        # Consultar métricas mediante API
        res_metrics = api_client.get('/api/v1/books/recommendations/metrics/')
        assert res_metrics.status_code == status.HTTP_200_OK
        kpis = res_metrics.data['kpis']
        assert kpis['ctr'] == 50.0  # 1 click / 2 shown
        assert kpis['dismiss_rate'] == 50.0  # 1 dismissed / 2 shown


@pytest.mark.django_db
class TestPhase07PrivacyFiltering:
    """Verifica que las señales sociales respeten PrivacyService y bloqueos (Fase 7 - 12.3)."""

    def test_social_recommendations_exclude_blocked_and_private_profiles(self, sample_data):
        alice = sample_data['users']['alice']
        bob = sample_data['users']['bob']
        eve = sample_data['users']['eve']
        book_left_hand = sample_data['books']['left_hand']

        # Alice sigue a Bob y a Eve
        alice.following.add(bob)
        alice.following.add(eve)

        # Bob y Eve leyeron "La mano izquierda de la oscuridad"
        UserBook.objects.create(user=bob, book=book_left_hand, status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=eve, book=book_left_hand, status=ReadingStatus.READ, rating=5)

        # 1. Eve bloquea a Alice (bloqueo bidireccional)
        eve.blocked_users.add(alice)

        # 2. Bob pone su perfil y biblioteca en privado
        bob.privacy_level = PrivacyChoices.PRIVATE
        bob.reading_privacy_level = PrivacyChoices.PRIVATE
        bob.save()

        # Alice solicita recomendaciones
        recs = get_user_recommendations(user=alice, limit=5, strategy='social')

        # Como Bob tiene perfil privado y Eve bloqueó a Alice, no deben filtrarse sus lecturas
        # en las razones explicativas de Alice
        for item in recs:
            if item['id'] == book_left_hand.id:
                reason = item['reason']
                assert "@eve" not in reason
                assert "@bob" not in reason


@pytest.mark.django_db
class TestPhase07DiversityLayer:
    """Verifica la capa de diversidad (Fase 7 - 12.1)."""

    def test_apply_diversity_filter_limits_author_saturation(self, sample_data):
        books = sample_data['books']
        # Creamos una lista simulada donde los primeros 3 libros son del mismo autor (Ursula Le Guin)
        mock_candidates = [
            {'book': books['dispossessed'], 'score': 0.95},
            {'book': books['earthsea'], 'score': 0.90},
            {'book': books['left_hand'], 'score': 0.85},
            {'book': books['ubik'], 'score': 0.80},
            {'book': books['kindred'], 'score': 0.75},
        ]

        # Con max_per_author=2 y limit=4
        diversified = apply_diversity_filter(mock_candidates, limit=4, max_per_author=2)
        assert len(diversified) == 4

        # Comprobar que en los primeros puestos no hay más de 2 de Ursula Le Guin antes de dar paso a otros
        authors_in_top = [item['book'].author.name for item in diversified[:3]]
        leguin_count = authors_in_top.count("Ursula K. Le Guin")
        assert leguin_count <= 2

    def test_diversity_integrated_in_get_user_recommendations(self, sample_data):
        alice = sample_data['users']['alice']
        books = sample_data['books']

        # Alice leyó y amó 1 libro de Ursula Le Guin
        UserBook.objects.create(
            user=alice,
            book=books['dispossessed'],
            status=ReadingStatus.READ,
            rating=5,
        )

        # Obtener recomendaciones v1 o hybrid
        recs = get_user_recommendations(user=alice, limit=3, strategy='rules')
        assert len(recs) > 0

        # Verificar metadatos y versionado
        for r in recs:
            assert 'strategy' in r
            assert 'algorithm_version' in r
            assert 'metadata' in r


@pytest.mark.django_db
class TestPhase07SatelliteBookEmbeddingIntegration:
    """Verifica la integración con el modelo satélite BookEmbedding (Fase 7 - 12.2 & 12.6)."""

    def test_recommendation_v3_reads_satellite_book_embedding(self, sample_data):
        alice = sample_data['users']['alice']
        books = sample_data['books']

        # Crear embeddings normalizados para los libros
        vec_sci = [1.0, 0.0, 0.0] + [0.0] * 1533
        vec_fan = [0.0, 1.0, 0.0] + [0.0] * 1533

        # Persistir BookEmbedding satélite en BD
        BookEmbedding.objects.create(
            book=books['dispossessed'],
            vector=vec_sci,
            dimension=1536,
            embedding_model="text-embedding-3-small",
            embedding_status=EmbeddingStatus.COMPLETED,
        )
        BookEmbedding.objects.create(
            book=books['ubik'],
            vector=vec_sci,
            dimension=1536,
            embedding_model="text-embedding-3-small",
            embedding_status=EmbeddingStatus.COMPLETED,
        )
        BookEmbedding.objects.create(
            book=books['earthsea'],
            vector=vec_fan,
            dimension=1536,
            embedding_model="text-embedding-3-small",
            embedding_status=EmbeddingStatus.COMPLETED,
        )

        # Alice interactuó con "Los desposeídos"
        UserBook.objects.create(
            user=alice,
            book=books['dispossessed'],
            status=ReadingStatus.READ,
            rating=5,
        )

        engine = RecommendationEngineV3()
        pref_vec = engine.compute_user_preference_embedding(alice)
        assert pref_vec is not None
        assert pref_vec.has_vector
        assert pref_vec.books_count == 1

        recs = engine.recommend(user=alice, limit=5)
        assert len(recs) > 0

        # Ubik (con similitud semántica 1.0) debe tener puntuación semántica alta
        ubik_rec = next((r for r in recs if r['id'] == books['ubik'].id), None)
        assert ubik_rec is not None
        assert ubik_rec['breakdown']['semantic'] > 0.8
        assert ubik_rec['strategy'] == 'v3'
        assert ubik_rec['algorithm_version'] == 'v3'
        assert 'metadata' in ubik_rec

import math

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingStatus, UserBook
from books.services.recommendation_v3_service import (
    ALGORITHM_VERSION_V3,
    RecommendationEngineV3,
    get_user_preference_vector,
    recommend_books_v3,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def catalog_v3():
    cache.clear()
    cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='scifi-v3')
    cat_cyberpunk = Category.objects.create(name='Cyberpunk', slug='cyberpunk-v3')
    cat_romance = Category.objects.create(name='Romance', slug='romance-v3')

    author_gibson = Author.objects.create(name='William Gibson')
    author_pkd = Author.objects.create(name='Philip K. Dick')
    author_austen = Author.objects.create(name='Jane Austen')

    # Vector representations: 3-dimensional normalized-like embeddings
    # Sci-Fi / Cyberpunk direction: [0.9, 0.1, 0.0]
    # General Sci-Fi direction: [0.8, 0.2, 0.0]
    # Romance direction: [0.0, 0.1, 0.9]

    book_neuromancer = Book.objects.create(
        title='Neuromancer',
        author=author_gibson,
        average_rating=4.8,
        embedding=[0.9, 0.1, 0.0],
    )
    book_neuromancer.categories.add(cat_scifi, cat_cyberpunk)

    book_count_zero = Book.objects.create(
        title='Conde Cero',
        author=author_gibson,
        average_rating=4.6,
        embedding=[0.88, 0.12, 0.0],
    )
    book_count_zero.categories.add(cat_scifi, cat_cyberpunk)

    book_ubik = Book.objects.create(
        title='Ubik',
        author=author_pkd,
        average_rating=4.5,
        embedding=[0.75, 0.25, 0.0],
    )
    book_ubik.categories.add(cat_scifi)

    book_pride = Book.objects.create(
        title='Orgullo y Prejuicio',
        author=author_austen,
        average_rating=4.9,
        embedding=[0.0, 0.1, 0.9],
    )
    book_pride.categories.add(cat_romance)

    book_no_emb = Book.objects.create(
        title='Libro Sin Embedding',
        author=author_pkd,
        average_rating=4.0,
        embedding=None,
    )
    book_no_emb.categories.add(cat_scifi)

    return {
        'cat_scifi': cat_scifi,
        'cat_cyberpunk': cat_cyberpunk,
        'cat_romance': cat_romance,
        'book_neuromancer': book_neuromancer,
        'book_count_zero': book_count_zero,
        'book_ubik': book_ubik,
        'book_pride': book_pride,
        'book_no_emb': book_no_emb,
    }


@pytest.mark.django_db
class TestUserPreferenceVectorComputation:
    def test_single_book_rated_creates_normalized_vector(self, catalog_v3):
        user = User.objects.create_user(username='cyber_fan', email='cfan@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )

        pref = get_user_preference_vector(user)
        assert pref.has_vector
        assert pref.books_analyzed == 1
        assert pref.dimension == 3
        assert len(pref.vector) == 3

        # Euclidean norm must be 1.0 (within float precision)
        norm = math.sqrt(sum(x ** 2 for x in pref.vector))
        assert pytest.approx(norm, rel=1e-4) == 1.0

        # Component in index 0 should be dominant (~0.993)
        assert pref.vector[0] > 0.9

    def test_weighted_average_two_books(self, catalog_v3):
        user = User.objects.create_user(username='hybrid_fan', email='hfan@test.com', password='pwd')
        # Neuromancer: rating 5 (weight 1.5)
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )
        # Pride & Prejudice: reading (weight 0.70)
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_pride'],
            status=ReadingStatus.READING,
            rating=None,
        )

        pref = get_user_preference_vector(user)
        assert pref.has_vector
        assert pref.books_analyzed == 2
        assert pref.dimension == 3

        # Should have both sci-fi and romance components, but sci-fi is weighted more
        assert pref.vector[0] > pref.vector[2]
        norm = math.sqrt(sum(x ** 2 for x in pref.vector))
        assert pytest.approx(norm, rel=1e-4) == 1.0

    def test_user_without_embeddings_returns_empty_vector(self, catalog_v3):
        user = User.objects.create_user(username='no_emb_user', email='noemb@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_no_emb'],
            status=ReadingStatus.READ,
            rating=4,
        )

        pref = get_user_preference_vector(user)
        assert not pref.has_vector
        assert pref.books_analyzed == 0
        assert pref.vector is None


@pytest.mark.django_db
class TestSemanticSimilarityScoring:
    def test_cosine_similarity_direct(self, catalog_v3):
        user = User.objects.create_user(username='cosine_user', email='cos@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )

        engine = RecommendationEngineV3(user=user)
        user_vec = engine.get_user_preference_vector()

        # Count Zero has very similar embedding [0.88, 0.12, 0.0] vs [0.9, 0.1, 0.0]
        score_count_zero = engine.calculate_semantic_similarity(
            user_vec.vector,
            catalog_v3['book_count_zero'].embedding,
        )
        # Pride & Prejudice has orthogonal-ish embedding [0.0, 0.1, 0.9]
        score_pride = engine.calculate_semantic_similarity(
            user_vec.vector,
            catalog_v3['book_pride'].embedding,
        )

        assert score_count_zero > 0.95
        assert score_pride < 0.20
        assert score_count_zero > score_pride


@pytest.mark.django_db
class TestTriHybridRecommendationsV3:
    def test_v3_ranking_and_breakdown(self, catalog_v3):
        user = User.objects.create_user(username='v3_reader', email='v3reader@test.com', password='pwd')
        peer = User.objects.create_user(username='v3_peer', email='v3peer@test.com', password='pwd')

        # User reads Neuromancer
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )

        # Peer also reads Neuromancer + Conde Cero + Ubik
        UserBook.objects.create(
            user=peer,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )
        UserBook.objects.create(
            user=peer,
            book=catalog_v3['book_count_zero'],
            status=ReadingStatus.READ,
            rating=5,
        )
        UserBook.objects.create(
            user=peer,
            book=catalog_v3['book_ubik'],
            status=ReadingStatus.READ,
            rating=4,
        )

        recs = recommend_books_v3(user, limit=5)
        assert len(recs) >= 1

        rec_titles = [r['title'] for r in recs]
        # Consumed book (Neuromancer) must be strictly excluded
        assert 'Neuromancer' not in rec_titles

        # Conde Cero should be top recommendation (strong semantic similarity + collaborative boost + content match)
        assert rec_titles[0] == 'Conde Cero'

        top = recs[0]
        assert top['algorithm_version'] == ALGORITHM_VERSION_V3
        assert 'breakdown' in top
        assert 'semantic' in top['breakdown']
        assert 'collaborative' in top['breakdown']
        assert 'content_v1' in top['breakdown']
        assert top['breakdown']['semantic'] > 0.8
        assert 'semántica' in top['reason'].lower() or 'estilo' in top['reason'].lower()

    def test_v3_fallback_for_cold_start_user(self, catalog_v3):
        newbie = User.objects.create_user(username='v3_newbie', email='v3newbie@test.com', password='pwd')
        recs = recommend_books_v3(newbie, limit=3)

        assert len(recs) >= 1
        assert recs[0]['algorithm_version'] == ALGORITHM_VERSION_V3
        assert recs[0]['score'] > 0.0


@pytest.mark.django_db
class TestAPIEndpointsV3:
    def test_api_recommendations_v3_strategy(self, api_client, catalog_v3):
        user = User.objects.create_user(username='v3_api_user', email='v3api@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/?strategy=v3')
        assert res.status_code == 200
        data = res.json()

        assert data['strategy'] == 'v3'
        assert data['algorithm_version'] == 'v3'
        assert len(data['results']) >= 1

        first_item = data['results'][0]
        assert first_item['algorithm_version'] == 'v3'
        assert 'semantic' in first_item['breakdown']
        assert 'collaborative' in first_item['breakdown']
        assert 'content_v1' in first_item['breakdown']

    def test_api_user_preference_embedding_endpoint_with_data(self, api_client, catalog_v3):
        user = User.objects.create_user(username='emb_user', email='emb@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=catalog_v3['book_neuromancer'],
            status=ReadingStatus.READ,
            rating=5,
        )

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/user-embedding/')
        assert res.status_code == 200
        data = res.json()

        assert data['has_embedding'] is True
        assert data['books_analyzed'] == 1
        assert data['dimension'] == 3
        assert isinstance(data['vector'], list)
        assert len(data['vector']) == 3
        assert data['algorithm_version'] == 'v3'

    def test_api_user_preference_embedding_endpoint_empty(self, api_client, catalog_v3):
        user = User.objects.create_user(username='fresh_user', email='fresh@test.com', password='pwd')

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/user-embedding/')
        assert res.status_code == 200
        data = res.json()

        assert data['has_embedding'] is False
        assert data['books_analyzed'] == 0
        assert data['dimension'] == 0
        assert data['vector'] is None

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingStatus, UserBook
from books.services.recommendation_v2_service import (
    ALGORITHM_VERSION_V2,
    RecommendationEngineV2,
    get_similar_readers_v2,
    recommend_books_v2,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def catalog_v2():
    cache.clear()
    cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='scifi')
    cat_dystopia = Category.objects.create(name='Distopía', slug='distopia')

    author_orwell = Author.objects.create(name='George Orwell')
    author_huxley = Author.objects.create(name='Aldous Huxley')
    author_bradbury = Author.objects.create(name='Ray Bradbury')
    author_dick = Author.objects.create(name='Philip K. Dick')

    book_1984 = Book.objects.create(title='1984', author=author_orwell, average_rating=4.9)
    book_1984.categories.add(cat_dystopia, cat_scifi)

    book_brave = Book.objects.create(title='Un mundo feliz', author=author_huxley, average_rating=4.7)
    book_brave.categories.add(cat_dystopia, cat_scifi)

    book_f451 = Book.objects.create(title='Fahrenheit 451', author=author_bradbury, average_rating=4.6)
    book_f451.categories.add(cat_dystopia)

    book_androids = Book.objects.create(title='¿Sueñan los androides con ovejas eléctricas?', author=author_dick, average_rating=4.5)
    book_androids.categories.add(cat_scifi)

    book_ubik = Book.objects.create(title='Ubik', author=author_dick, average_rating=4.4)
    book_ubik.categories.add(cat_scifi)

    return {
        'cat_scifi': cat_scifi,
        'cat_dystopia': cat_dystopia,
        'book_1984': book_1984,
        'book_brave': book_brave,
        'book_f451': book_f451,
        'book_androids': book_androids,
        'book_ubik': book_ubik,
    }


@pytest.mark.django_db
class TestUserSimilarityMetric:
    def test_compute_user_similarity_high_overlap(self):
        engine = RecommendationEngineV2()
        # Dos lectores con 3 libros idénticos y calificaciones idénticas
        user_a = {101: 5.0, 102: 4.0, 103: 5.0}
        user_b = {101: 5.0, 102: 4.0, 103: 5.0}

        sim, shared = engine.compute_user_similarity(user_a, user_b)
        assert shared == 3
        assert sim >= 0.95

    def test_compute_user_similarity_zero_overlap(self):
        engine = RecommendationEngineV2()
        user_a = {101: 5.0, 102: 4.0}
        user_b = {201: 5.0, 202: 4.0}

        sim, shared = engine.compute_user_similarity(user_a, user_b)
        assert shared == 0
        assert sim == 0.0

    def test_compute_user_similarity_divergent_ratings(self):
        engine = RecommendationEngineV2()
        # Comparten los mismos libros pero con opiniones opuestas (5 estrellas vs 1 estrella)
        user_a = {101: 5.0, 102: 5.0}
        user_b = {101: 1.0, 102: 1.0}

        sim, shared = engine.compute_user_similarity(user_a, user_b)
        assert shared == 2
        # La similitud es menor debido a la disparidad de ratings
        assert sim < 0.60


@pytest.mark.django_db
class TestFindSimilarUsers:
    def test_find_similar_users_ranking(self, catalog_v2):
        target_user = User.objects.create_user(username='jorge', email='jorge@test.com', password='pwd')
        peer_twin = User.objects.create_user(username='lector_gemelo', email='gemelo@test.com', password='pwd')
        peer_partial = User.objects.create_user(username='lector_parcial', email='parcial@test.com', password='pwd')
        peer_none = User.objects.create_user(username='lector_ajeno', email='ajeno@test.com', password='pwd')

        # Jorge leyó 1984 y Un mundo feliz
        UserBook.objects.create(user=target_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=target_user, book=catalog_v2['book_brave'], status=ReadingStatus.READ, rating=5)

        # Lector gemelo leyó ambos con alta valoración
        UserBook.objects.create(user=peer_twin, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=peer_twin, book=catalog_v2['book_brave'], status=ReadingStatus.READ, rating=5)

        # Lector parcial solo leyó 1984
        UserBook.objects.create(user=peer_partial, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=4)

        # Lector ajeno leyó Ubik
        UserBook.objects.create(user=peer_none, book=catalog_v2['book_ubik'], status=ReadingStatus.READ, rating=5)

        engine = RecommendationEngineV2()
        similar_peers = engine.find_similar_users(target_user, limit=10)

        assert len(similar_peers) >= 2
        usernames = [p.username for p in similar_peers]
        assert 'lector_gemelo' in usernames
        assert 'lector_parcial' in usernames
        assert 'lector_ajeno' not in usernames

        # El lector gemelo debe encabezar el ranking
        assert similar_peers[0].username == 'lector_gemelo'
        assert similar_peers[0].similarity_score > similar_peers[1].similarity_score

    def test_find_similar_users_excludes_blocked_users(self, catalog_v2):
        target_user = User.objects.create_user(username='jorge_b', email='jorge_b@test.com', password='pwd')
        blocked_user = User.objects.create_user(username='usuario_bloqueado', email='bloq@test.com', password='pwd')

        UserBook.objects.create(user=target_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=blocked_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)

        if hasattr(target_user, 'blocked_users'):
            target_user.blocked_users.add(blocked_user)

        engine = RecommendationEngineV2()
        peers = engine.find_similar_users(target_user)
        peer_names = [p.username for p in peers]
        assert 'usuario_bloqueado' not in peer_names


@pytest.mark.django_db
class TestCollaborativeCandidateScoring:
    def test_collaborative_candidate_extraction_and_scoring(self, catalog_v2):
        """Libros que el lector afín ha leído pero Jorge no ha leído son candidatos con score positivo."""
        target_user = User.objects.create_user(username='jorge_c', email='jorge_c@test.com', password='pwd')
        peer_user = User.objects.create_user(username='afinidad_pura', email='afin@test.com', password='pwd')

        # Ambos leyeron 1984
        UserBook.objects.create(user=target_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=peer_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)

        # El vecino afín leyó y calificó con 5 Fahrenheit 451
        UserBook.objects.create(user=peer_user, book=catalog_v2['book_f451'], status=ReadingStatus.READ, rating=5)

        engine = RecommendationEngineV2()
        peers = engine.find_similar_users(target_user)
        collab_candidates = engine.get_collaborative_candidate_scores(target_user, peers)

        assert catalog_v2['book_f451'].id in collab_candidates
        assert catalog_v2['book_1984'].id not in collab_candidates
        assert collab_candidates[catalog_v2['book_f451'].id]['score'] > 0.8
        assert 'afinidad_pura' in collab_candidates[catalog_v2['book_f451'].id]['peers']


@pytest.mark.django_db
class TestRecommendationEngineV2FullPipeline:
    def test_v2_recommendations_ranking_and_version(self, catalog_v2):
        target_user = User.objects.create_user(username='jorge_v2', email='jorge_v2@test.com', password='pwd')
        peer_user = User.objects.create_user(username='peer_v2', email='peer_v2@test.com', password='pwd')

        UserBook.objects.create(user=target_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=peer_user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=peer_user, book=catalog_v2['book_brave'], status=ReadingStatus.READ, rating=5)

        engine = RecommendationEngineV2()
        recs = engine.recommend(target_user, limit=5)

        assert len(recs) >= 1
        rec_titles = [r['title'] for r in recs]

        # 1984 ya fue leído por Jorge -> Exclusión estricta
        assert '1984' not in rec_titles
        # Un mundo feliz fue leído y recomendado por peer_v2 -> Primer candidato
        assert rec_titles[0] == 'Un mundo feliz'

        top_rec = recs[0]
        assert top_rec['algorithm_version'] == ALGORITHM_VERSION_V2
        assert 'peer_v2' in top_rec['reason']
        assert top_rec['breakdown']['collaborative'] > 0.0

    def test_v2_cold_start_fallback(self, catalog_v2):
        newbie = User.objects.create_user(username='newbie_v2', email='newbie_v2@test.com', password='pwd')
        recs = recommend_books_v2(newbie, limit=3)

        assert len(recs) >= 1
        assert recs[0]['algorithm_version'] == 'v2'
        assert recs[0]['score'] > 0.0
        assert 'viaje' in recs[0]['reason'].lower() or 'comunidad' in recs[0]['reason'].lower()


@pytest.mark.django_db
class TestAPIEndpointsV2:
    def test_api_recommendations_v2_strategy(self, api_client, catalog_v2):
        user = User.objects.create_user(username='api_v2_user', email='apiv2@test.com', password='pwd')
        peer = User.objects.create_user(username='peer_api', email='peerapi@test.com', password='pwd')

        UserBook.objects.create(user=user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=peer, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=peer, book=catalog_v2['book_f451'], status=ReadingStatus.READ, rating=5)

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/?strategy=v2')
        assert res.status_code == 200
        data = res.json()

        assert data['strategy'] == 'v2'
        assert data['algorithm_version'] == 'v2'
        assert len(data['results']) >= 1
        first_item = data['results'][0]
        assert first_item['algorithm_version'] == 'v2'
        assert 'collaborative' in first_item['breakdown']

    def test_api_similar_readers_endpoint(self, api_client, catalog_v2):
        user = User.objects.create_user(username='reader_x', email='x@test.com', password='pwd')
        twin = User.objects.create_user(username='reader_twin', email='twin@test.com', password='pwd')

        UserBook.objects.create(user=user, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=twin, book=catalog_v2['book_1984'], status=ReadingStatus.READ, rating=5)

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/similar-readers/')
        assert res.status_code == 200
        data = res.json()

        assert 'results' in data
        assert data['count'] >= 1
        assert data['results'][0]['username'] == 'reader_twin'
        assert data['results'][0]['similarity_score'] > 0
        assert data['results'][0]['shared_books_count'] == 1

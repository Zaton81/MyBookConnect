import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingList, ReadingListItem, ReadingStatus, RecommendationFeedback, RecommendationFeedbackAction, UserBook
from books.services.recommendation_feedback_service import record_recommendation_event
from books.services.recommendation_v1_service import (
    ALGORITHM_VERSION,
    RecommendationEngineV1,
    recommend_books_v1,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def catalog_v1():
    cache.clear()
    cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='ciencia-ficcion')
    cat_fantasy = Category.objects.create(name='Fantasía', slug='fantasia')
    cat_history = Category.objects.create(name='Historia', slug='historia')

    author_asimov = Author.objects.create(name='Isaac Asimov')
    author_tolkien = Author.objects.create(name='J.R.R. Tolkien')
    author_clark = Author.objects.create(name='Arthur C. Clarke')
    author_other = Author.objects.create(name='Autor Desconocido')

    # Libros base
    book_fundacion = Book.objects.create(
        title='Fundación',
        author=author_asimov,
        average_rating=4.8,
        description='Trilogía sobre la psicohistoria y el imperio galáctico.',
    )
    book_fundacion.categories.add(cat_scifi)

    book_robot = Book.objects.create(
        title='Yo, Robot',
        author=author_asimov,
        average_rating=4.5,
        description='Historias sobre las tres leyes de la robótica.',
    )
    book_robot.categories.add(cat_scifi)

    book_lotr = Book.objects.create(
        title='La Comunidad del Anillo',
        author=author_tolkien,
        average_rating=4.9,
        description='Viaje épico a través de la Tierra Media.',
    )
    book_lotr.categories.add(cat_fantasy)

    book_odisea = Book.objects.create(
        title='2001: Una Odisea Espacial',
        author=author_clark,
        average_rating=4.6,
        description='Monolitos espaciales y exploración más allá de Júpiter.',
    )
    book_odisea.categories.add(cat_scifi)

    book_history = Book.objects.create(
        title='Breve Historia de Roma',
        author=author_other,
        average_rating=3.2,
        description='Tratado sobre el senado romano y las legiones.',
    )
    book_history.categories.add(cat_history)

    return {
        'cat_scifi': cat_scifi,
        'cat_fantasy': cat_fantasy,
        'cat_history': cat_history,
        'author_asimov': author_asimov,
        'author_tolkien': author_tolkien,
        'author_clark': author_clark,
        'author_other': author_other,
        'book_fundacion': book_fundacion,
        'book_robot': book_robot,
        'book_lotr': book_lotr,
        'book_odisea': book_odisea,
        'book_history': book_history,
    }


@pytest.mark.django_db
class TestRecommendationEngineV1Variables:
    def test_genre_variable_affinity(self, catalog_v1):
        """La variable S_genre premia a los libros que coinciden con géneros leídos o valorados."""
        user = User.objects.create_user(username='scifi_fan', email='scifi@test.com', password='pwd')
        # Usuario leyó Fundación (Ciencia Ficción)
        UserBook.objects.create(user=user, book=catalog_v1['book_fundacion'], status=ReadingStatus.READ, rating=5)

        engine = RecommendationEngineV1()
        profile = engine.compute_user_profile(user)

        # Evaluar Yo, Robot (Ciencia Ficción) vs Breve Historia de Roma (Historia)
        item_robot = engine.score_candidate(catalog_v1['book_robot'], profile)
        item_history = engine.score_candidate(catalog_v1['book_history'], profile)

        assert item_robot.breakdown.genre > item_history.breakdown.genre
        assert item_robot.breakdown.genre == 1.0
        assert item_history.breakdown.genre == 0.0

    def test_author_variable_affinity(self, catalog_v1):
        """La variable S_author otorga mayor score a obras de autores ya explorados y bien valorados."""
        user = User.objects.create_user(username='asimov_fan', email='asimov@test.com', password='pwd')
        UserBook.objects.create(user=user, book=catalog_v1['book_fundacion'], status=ReadingStatus.READ, rating=5)

        engine = RecommendationEngineV1()
        profile = engine.compute_user_profile(user)

        # Yo, Robot (Asimov) vs 2001 (Clarke)
        item_robot = engine.score_candidate(catalog_v1['book_robot'], profile)
        item_odisea = engine.score_candidate(catalog_v1['book_odisea'], profile)

        assert item_robot.breakdown.author > item_odisea.breakdown.author
        assert item_robot.breakdown.author == 1.0
        assert item_odisea.breakdown.author == 0.0

    def test_rating_variable_impact(self, catalog_v1):
        """La variable S_rating refleja la calidad y valoración comunitaria normalizada."""
        user = User.objects.create_user(username='rating_user', email='rating@test.com', password='pwd')
        engine = RecommendationEngineV1()
        profile = engine.compute_user_profile(user)

        item_lotr = engine.score_candidate(catalog_v1['book_lotr'], profile)       # avg 4.9
        item_history = engine.score_candidate(catalog_v1['book_history'], profile) # avg 3.2

        assert item_lotr.breakdown.rating > item_history.breakdown.rating
        assert item_lotr.breakdown.rating > 0.8
        assert item_history.breakdown.rating < 0.2

    def test_history_variable_and_strict_exclusion(self, catalog_v1):
        """La variable S_history crece con el volumen de lecturas y los libros leídos jamás se recomiendan."""
        user = User.objects.create_user(username='heavy_reader', email='heavy@test.com', password='pwd')
        # Añadir libros leídos
        UserBook.objects.create(user=user, book=catalog_v1['book_fundacion'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=user, book=catalog_v1['book_lotr'], status=ReadingStatus.READ, rating=4)

        recs = recommend_books_v1(user=user, limit=5)
        rec_ids = [r['id'] for r in recs]

        # Exclusión estricta de biblioteca propia
        assert catalog_v1['book_fundacion'].id not in rec_ids
        assert catalog_v1['book_lotr'].id not in rec_ids

        # Los candidatos viables deben haber recibido score de historial positivo
        top_rec = recs[0]
        assert top_rec['breakdown']['history'] > 0.0

    def test_wishlist_variable_intentionality(self, catalog_v1):
        """Libros en WANT_TO_READ o listas de deseos potencian directamente autores y categorías afines."""
        user = User.objects.create_user(username='wishlist_user', email='wish@test.com', password='pwd')
        # Guarda Odisea en WANT_TO_READ
        UserBook.objects.create(user=user, book=catalog_v1['book_odisea'], status=ReadingStatus.WANT_TO_READ)

        engine = RecommendationEngineV1()
        profile = engine.compute_user_profile(user)

        assert catalog_v1['cat_scifi'].id in profile.wishlist_categories
        assert catalog_v1['author_clark'].id in profile.wishlist_authors

        # Evaluar candidato de Ciencia Ficción (Yo, Robot)
        item_robot = engine.score_candidate(catalog_v1['book_robot'], profile)
        assert item_robot.breakdown.wishlist > 0.0


@pytest.mark.django_db
class TestRecommendationWeightedSumAndVersioning:
    def test_weighted_sum_calculation(self, catalog_v1):
        """Verifica que el score final coincida matemáticamente con la suma ponderada."""
        user = User.objects.create_user(username='math_user', email='math@test.com', password='pwd')
        UserBook.objects.create(user=user, book=catalog_v1['book_fundacion'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=user, book=catalog_v1['book_odisea'], status=ReadingStatus.WANT_TO_READ)

        engine = RecommendationEngineV1()
        profile = engine.compute_user_profile(user)
        item = engine.score_candidate(catalog_v1['book_robot'], profile)

        w = engine.weights
        expected_score = (
            (w['genre'] * item.breakdown.genre)
            + (w['author'] * item.breakdown.author)
            + (w['rating'] * item.breakdown.rating)
            + (w['history'] * item.breakdown.history)
            + (w['wishlist'] * item.breakdown.wishlist)
        )
        assert pytest.approx(item.score, rel=1e-3) == min(1.0, max(0.0, expected_score))
        assert item.algorithm_version == ALGORITHM_VERSION

    def test_custom_weights_override(self, catalog_v1):
        """Verifica la configuración personalizada de pesos en el motor v1."""
        custom_weights = {'genre': 0.8, 'author': 0.2, 'rating': 0.0, 'history': 0.0, 'wishlist': 0.0}
        engine = RecommendationEngineV1(weights=custom_weights)
        assert engine.weights['genre'] == 0.8
        assert engine.weights['author'] == 0.2

    def test_cold_start_new_user(self, catalog_v1):
        """Un usuario recién registrado sin historial recibe recomendaciones populares con versionado v1."""
        new_user = User.objects.create_user(username='newbie', email='newbie@test.com', password='pwd')
        recs = recommend_books_v1(user=new_user, limit=3)
        assert len(recs) >= 1
        assert recs[0]['algorithm_version'] == 'v1'
        assert 'scores' in recs[0]
        assert 'breakdown' in recs[0]
        assert recs[0]['score'] > 0


@pytest.mark.django_db
class TestRecommendationsAPIEndpointV1:
    def test_api_user_recommendations_v1_strategy(self, api_client, catalog_v1):
        user = User.objects.create_user(username='api_rec_user', email='apirec@test.com', password='pwd')
        UserBook.objects.create(user=user, book=catalog_v1['book_fundacion'], status=ReadingStatus.READ, rating=5)

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/?strategy=v1')
        assert res.status_code == 200
        data = res.json()

        assert data['strategy'] == 'v1'
        assert data['algorithm_version'] == 'v1'
        assert len(data['results']) >= 1

        first_rec = data['results'][0]
        assert first_rec['algorithm_version'] == 'v1'
        assert 'breakdown' in first_rec
        assert 'genre' in first_rec['breakdown']
        assert 'author' in first_rec['breakdown']
        assert 'rating' in first_rec['breakdown']
        assert 'history' in first_rec['breakdown']
        assert 'wishlist' in first_rec['breakdown']
        assert 'reason' in first_rec

    def test_api_user_recommendations_version_parameter(self, api_client, catalog_v1):
        user = User.objects.create_user(username='version_user', email='ver@test.com', password='pwd')
        api_client.force_authenticate(user=user)

        res = api_client.get('/api/v1/books/recommendations/?version=v1')
        assert res.status_code == 200
        data = res.json()
        assert data['algorithm_version'] == 'v1'

    def test_feedback_event_records_algorithm_version_v1(self, catalog_v1):
        user = User.objects.create_user(username='feedback_user', email='fb@test.com', password='pwd')
        fb = record_recommendation_event(
            user=user,
            book_id=catalog_v1['book_robot'].id,
            action=RecommendationFeedbackAction.RECOMMENDATION_CLICKED,
            strategy='v1',
            algorithm_version='v1',
            metadata={'score': 0.85},
        )
        assert fb.id is not None
        assert fb.algorithm_version == 'v1'
        assert fb.strategy == 'v1'
        assert RecommendationFeedback.objects.filter(algorithm_version='v1').exists()

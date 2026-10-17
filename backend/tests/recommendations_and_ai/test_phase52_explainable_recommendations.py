import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingStatus, UserBook
from books.services.recommendation_explanation_service import (
    RecommendationExplanationEngine,
    explain_recommendation,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def explain_catalog():
    cache.clear()
    cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='scifi-p52')
    cat_dystopia = Category.objects.create(name='Distopía', slug='distopia-p52')
    cat_fantasy = Category.objects.create(name='Fantasía', slug='fantasia-p52')

    author_herbert = Author.objects.create(name='Frank Herbert')
    author_orwell = Author.objects.create(name='George Orwell')
    author_asimov = Author.objects.create(name='Isaac Asimov')

    # Embeddings vectoriales sintéticos
    # Sci-Fi épico: [0.9, 0.1, 0.0]
    # Sci-Fi / Distopía: [0.85, 0.15, 0.0]
    # Fantasía: [0.0, 0.2, 0.8]

    book_dune = Book.objects.create(
        title='Dune',
        author=author_herbert,
        average_rating=4.9,
        embedding=[0.9, 0.1, 0.0],
    )
    book_dune.categories.add(cat_scifi)

    book_1984 = Book.objects.create(
        title='1984',
        author=author_orwell,
        average_rating=4.8,
        embedding=[0.85, 0.15, 0.0],
    )
    book_1984.categories.add(cat_scifi, cat_dystopia)

    book_foundation = Book.objects.create(
        title='Fundación',
        author=author_asimov,
        average_rating=4.7,
        embedding=[0.89, 0.11, 0.0],
    )
    book_foundation.categories.add(cat_scifi)

    book_messiah = Book.objects.create(
        title='El Mesías de Dune',
        author=author_herbert,
        average_rating=4.6,
        embedding=[0.91, 0.09, 0.0],
    )
    book_messiah.categories.add(cat_scifi)

    return {
        'cat_scifi': cat_scifi,
        'cat_dystopia': cat_dystopia,
        'cat_fantasy': cat_fantasy,
        'author_herbert': author_herbert,
        'author_orwell': author_orwell,
        'author_asimov': author_asimov,
        'book_dune': book_dune,
        'book_1984': book_1984,
        'book_foundation': book_foundation,
        'book_messiah': book_messiah,
    }


@pytest.mark.django_db
class TestExplainableMultiSignalEngine:
    def test_genre_evidence_extraction(self, explain_catalog):
        user = User.objects.create_user(username='scifi_lover', email='scl@test.com', password='pwd')
        # El usuario ha leído y calificado positivamente Fundación y 1984 (ambos Ciencia Ficción)
        UserBook.objects.create(
            user=user,
            book=explain_catalog['book_1984'],
            status=ReadingStatus.READ,
            rating=5,
        )
        UserBook.objects.create(
            user=user,
            book=explain_catalog['book_foundation'],
            status=ReadingStatus.READ,
            rating=4,
        )

        engine = RecommendationExplanationEngine()
        explanation = engine.explain(user=user, book=explain_catalog['book_dune'])

        genre_bullet = next((b for b in explanation.reasons if b.type == 'genre'), None)
        assert genre_bullet is not None
        assert '2 libros de Ciencia Ficción' in genre_bullet.text
        assert genre_bullet.metadata['liked_count'] == 2

    def test_author_anchor_book_evidence(self, explain_catalog):
        user = User.objects.create_user(username='herbert_fan', email='hbf@test.com', password='pwd')
        # El usuario valoró El Mesías de Dune con 5 estrellas
        UserBook.objects.create(
            user=user,
            book=explain_catalog['book_messiah'],
            status=ReadingStatus.READ,
            rating=5,
        )

        engine = RecommendationExplanationEngine()
        explanation = engine.explain(user=user, book=explain_catalog['book_dune'])

        author_bullet = next((b for b in explanation.reasons if b.type == 'author'), None)
        assert author_bullet is not None
        assert 'Has valorado El Mesías de Dune con 5 estrellas' in author_bullet.text
        assert author_bullet.metadata['rating'] == 5

    def test_semantic_similarity_evidence(self, explain_catalog):
        user = User.objects.create_user(username='asimov_fan', email='asf@test.com', password='pwd')
        # El usuario leyó Fundación (embedding [0.89, 0.11, 0.0]), que tiene alta similitud con Dune ([0.9, 0.1, 0.0])
        UserBook.objects.create(
            user=user,
            book=explain_catalog['book_foundation'],
            status=ReadingStatus.READ,
            rating=5,
        )

        engine = RecommendationExplanationEngine()
        explanation = engine.explain(user=user, book=explain_catalog['book_dune'])

        semantic_bullet = next((b for b in explanation.reasons if b.type == 'semantic'), None)
        assert semantic_bullet is not None
        assert 'Fundación' in semantic_bullet.text
        assert semantic_bullet.metadata['similarity'] > 0.90
        assert '%' in semantic_bullet.text

    def test_social_following_evidence(self, explain_catalog):
        user = User.objects.create_user(username='social_reader', email='soc@test.com', password='pwd')
        friend1 = User.objects.create_user(username='amigo1', email='am1@test.com', password='pwd')
        friend2 = User.objects.create_user(username='amigo2', email='am2@test.com', password='pwd')

        user.following.add(friend1, friend2)

        # Ambos amigos leyeron Dune
        UserBook.objects.create(user=friend1, book=explain_catalog['book_dune'], status=ReadingStatus.READ)
        UserBook.objects.create(user=friend2, book=explain_catalog['book_dune'], status=ReadingStatus.READ)

        engine = RecommendationExplanationEngine()
        explanation = engine.explain(user=user, book=explain_catalog['book_dune'])

        social_bullet = next((b for b in explanation.reasons if b.type == 'social'), None)
        assert social_bullet is not None
        assert '@amigo1' in social_bullet.text
        assert '@amigo2' in social_bullet.text
        assert 'han leído este libro' in social_bullet.text

    def test_collaborative_evidence(self, explain_catalog):
        user = User.objects.create_user(username='collab_reader', email='col@test.com', password='pwd')
        breakdown = {
            'collaborative': 0.75,
            'shared_peers': 2,
            'top_peer': 'lector_gemelo',
        }

        explanation = explain_recommendation(
            user=user,
            book=explain_catalog['book_dune'],
            breakdown=breakdown,
        )

        collab_bullet = next((b for b in explanation['reasons'] if b['type'] == 'collaborative'), None)
        assert collab_bullet is not None
        assert 'lector_gemelo' in collab_bullet['text']
        assert collab_bullet['confidence'] == 0.75

    def test_full_dune_example_multi_signal(self, explain_catalog):
        """
        Prueba el ejemplo de especificación canónico:
        Te recomendamos Dune porque:
        ✓ te han gustado 2 libros de Ciencia Ficción;
        ✓ has valorado El Mesías de Dune con 5 estrellas;
        ✓ tiene similitud semántica alta con Fundación;
        ✓ usuarios que sigues lo han leído.
        """
        user = User.objects.create_user(username='complete_user', email='comp@test.com', password='pwd')
        friend = User.objects.create_user(username='amigo_dune', email='ad@test.com', password='pwd')
        user.following.add(friend)

        # 1. Libros de Ciencia Ficción leídos
        UserBook.objects.create(user=user, book=explain_catalog['book_1984'], status=ReadingStatus.READ, rating=5)
        UserBook.objects.create(user=user, book=explain_catalog['book_foundation'], status=ReadingStatus.READ, rating=4)

        # 2. Libro previo del mismo autor calificado con 5 estrellas
        UserBook.objects.create(user=user, book=explain_catalog['book_messiah'], status=ReadingStatus.READ, rating=5)

        # 3. Amigo que leyó Dune
        UserBook.objects.create(user=friend, book=explain_catalog['book_dune'], status=ReadingStatus.READ)

        engine = RecommendationExplanationEngine()
        explanation = engine.explain(user=user, book=explain_catalog['book_dune'])

        assert explanation.headline == "Te recomendamos Dune porque:"
        assert len(explanation.reasons) >= 4

        bullet_types = [b.type for b in explanation.reasons]
        assert 'genre' in bullet_types
        assert 'author' in bullet_types
        assert 'semantic' in bullet_types
        assert 'social' in bullet_types


@pytest.mark.django_db
class TestExplainableRecommendationsAPI:
    def test_recommendations_endpoint_includes_explanation_object(self, api_client, explain_catalog):
        user = User.objects.create_user(username='api_rec_user', email='apirec@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=explain_catalog['book_foundation'],
            status=ReadingStatus.READ,
            rating=5,
        )

        api_client.force_authenticate(user=user)
        res = api_client.get('/api/v1/books/recommendations/?strategy=v3')
        assert res.status_code == 200
        data = res.json()

        assert 'results' in data
        assert len(data['results']) >= 1

        first_rec = data['results'][0]
        assert 'explanation' in first_rec
        expl = first_rec['explanation']
        assert 'headline' in expl
        assert 'reasons' in expl
        assert 'primary_reason' in expl
        assert len(expl['reasons']) >= 1
        assert first_rec['reason'] == expl['primary_reason']

    def test_book_recommendation_explain_endpoint(self, api_client, explain_catalog):
        user = User.objects.create_user(username='explain_api_user', email='explapi@test.com', password='pwd')
        UserBook.objects.create(
            user=user,
            book=explain_catalog['book_1984'],
            status=ReadingStatus.READ,
            rating=5,
        )

        api_client.force_authenticate(user=user)
        book_id = explain_catalog['book_dune'].id
        res = api_client.get(f'/api/v1/books/recommendations/{book_id}/explain/')
        assert res.status_code == 200
        data = res.json()

        assert data['book_id'] == book_id
        assert data['book_title'] == 'Dune'
        assert 'headline' in data
        assert 'reasons' in data
        assert len(data['reasons']) >= 1
        assert data['total_signals'] >= 1
        assert data['algorithm_version'] == 'v3'

    def test_book_recommendation_explain_anonymous_rejected(self, api_client, explain_catalog):
        book_id = explain_catalog['book_dune'].id
        res = api_client.get(f'/api/v1/books/recommendations/{book_id}/explain/')
        assert res.status_code in (401, 403)

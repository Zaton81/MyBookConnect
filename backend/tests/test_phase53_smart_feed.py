"""
Suite de pruebas para la Fase 53 — Feed Inteligente (Smart Feed).

Verifica:
1. Ponderación multi-factor: recency, relationship, engagement y content relevance.
2. Detección y priorización de libros en la lista de deseos (wishlist).
3. Señales explicativas del feed (feed_signal).
4. Modo inteligente vs modo cronológico (?mode=chronological).
5. Endpoints REST (/api/v1/users/feed/ y /api/v1/books/feed/).
6. Respeto estricto a usuarios bloqueados y filtros por tipo de actividad.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from books.models import Author, Book, Category, ReadingStatus, Review, ReviewComment, ReviewLike, UserBook
from users.models import Activity, ActivityType
from users.smart_feed_service import SmartFeedRankingEngine, get_smart_feed

User = get_user_model()


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def feed_environment(db):
    """Crea un entorno de prueba con observador, amigos, libros, categorías e interacciones."""
    # 1. Usuarios
    observer = User.objects.create_user(username='observer', email='obs@test.com', password='pwd')
    friend_mutual = User.objects.create_user(username='best_friend', email='friend@test.com', password='pwd')
    casual_follow = User.objects.create_user(username='casual_user', email='casual@test.com', password='pwd')
    stranger = User.objects.create_user(username='stranger', email='stranger@test.com', password='pwd')
    blocked_user = User.objects.create_user(username='toxic_user', email='toxic@test.com', password='pwd')

    # Relaciones sociales
    observer.following.add(friend_mutual)
    friend_mutual.following.add(observer)  # Mutuo
    observer.following.add(casual_follow)  # Unilateral
    observer.following.add(blocked_user)   # Seguido pero bloqueado
    observer.blocked_users.add(blocked_user)

    # 2. Categorías y Autores
    cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='ciencia-ficcion')
    cat_romance = Category.objects.create(name='Romance', slug='romance')
    author_asimov = Author.objects.create(name='Isaac Asimov')
    author_other = Author.objects.create(name='Otro Autor')

    # 3. Libros
    book_wishlist = Book.objects.create(title='Dune', isbn='9780441172719', author=author_asimov, average_rating=4.8)
    book_wishlist.categories.add(cat_scifi)

    book_favorite_genre = Book.objects.create(title='Fundación', isbn='9780553293357', author=author_asimov, average_rating=4.7)
    book_favorite_genre.categories.add(cat_scifi)

    book_neutral = Book.objects.create(title='Novela Casual', isbn='9780000000001', author=author_other, average_rating=3.2)
    book_neutral.categories.add(cat_romance)

    # 4. Biblioteca de observer: le gusta la Ciencia Ficción y tiene Dune en Wishlist
    UserBook.objects.create(
        user=observer,
        book=book_favorite_genre,
        status=ReadingStatus.READ,
        rating=5,
    )
    UserBook.objects.create(
        user=observer,
        book=book_wishlist,
        status=ReadingStatus.WANT_TO_READ,
        wishlist=True,
    )

    # 5. Interacción previa: observer le dio like a una reseña pasada de best_friend
    past_review = Review.objects.create(
        user=friend_mutual,
        book=book_neutral,
        rating=8,
        title='Reseña pasada',
        text='Buena lectura del mes pasado.',
    )
    ReviewLike.objects.create(user=observer, review=past_review)

    return {
        'observer': observer,
        'friend_mutual': friend_mutual,
        'casual_follow': casual_follow,
        'stranger': stranger,
        'blocked_user': blocked_user,
        'cat_scifi': cat_scifi,
        'book_wishlist': book_wishlist,
        'book_favorite_genre': book_favorite_genre,
        'book_neutral': book_neutral,
    }


@pytest.mark.django_db
class TestSmartFeedRankingEngine:
    def test_recency_decay_calculation(self, feed_environment):
        engine = SmartFeedRankingEngine()
        obs = feed_environment['observer']
        friend = feed_environment['friend_mutual']
        book = feed_environment['book_neutral']
        ctx = engine.build_user_context(obs)
        now = timezone.now()

        # Actividad reciente (1 hora)
        act_recent = Activity.objects.create(
            user=friend,
            type=ActivityType.BOOK_FINISHED,
            book=book,
        )
        act_recent.created_at = now - timedelta(hours=1)
        act_recent.save()

        # Actividad antigua (5 días = 120 horas)
        act_old = Activity.objects.create(
            user=friend,
            type=ActivityType.BOOK_FINISHED,
            book=book,
        )
        act_old.created_at = now - timedelta(days=5)
        act_old.save()

        score_recent, _ = engine.compute_score(act_recent, ctx, now=now)
        score_old, _ = engine.compute_score(act_old, ctx, now=now)

        assert score_recent > score_old
        assert (score_recent - score_old) >= 0.20

    def test_relationship_and_mutual_following(self, feed_environment):
        engine = SmartFeedRankingEngine()
        obs = feed_environment['observer']
        mutual = feed_environment['friend_mutual']
        casual = feed_environment['casual_follow']
        book = feed_environment['book_neutral']
        ctx = engine.build_user_context(obs)
        now = timezone.now()

        # Actividad de amigo mutuo con interacción previa
        act_mutual = Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_ADDED,
            book=book,
        )
        act_mutual.created_at = now - timedelta(hours=2)
        act_mutual.save()

        # Actividad idéntica de seguido casual
        act_casual = Activity.objects.create(
            user=casual,
            type=ActivityType.BOOK_ADDED,
            book=book,
        )
        act_casual.created_at = now - timedelta(hours=2)
        act_casual.save()

        score_mutual, sig_mutual = engine.compute_score(act_mutual, ctx, now=now)
        score_casual, _ = engine.compute_score(act_casual, ctx, now=now)

        assert score_mutual > score_casual
        assert sig_mutual == "Amistad mutua"

    def test_content_relevance_prioritizes_wishlist(self, feed_environment):
        engine = SmartFeedRankingEngine()
        obs = feed_environment['observer']
        friend = feed_environment['casual_follow']
        book_wishlist = feed_environment['book_wishlist']
        book_neutral = feed_environment['book_neutral']
        ctx = engine.build_user_context(obs)
        now = timezone.now()

        # Amigo termina un libro que está en la wishlist de observer
        act_wishlist = Activity.objects.create(
            user=friend,
            type=ActivityType.BOOK_FINISHED,
            book=book_wishlist,
        )
        act_wishlist.created_at = now - timedelta(hours=5)
        act_wishlist.save()

        # Mismo amigo termina un libro neutral
        act_neutral = Activity.objects.create(
            user=friend,
            type=ActivityType.BOOK_FINISHED,
            book=book_neutral,
        )
        act_neutral.created_at = now - timedelta(hours=5)
        act_neutral.save()

        score_wishlist, sig_wishlist = engine.compute_score(act_wishlist, ctx, now=now)
        score_neutral, _ = engine.compute_score(act_neutral, ctx, now=now)

        assert score_wishlist > score_neutral
        assert sig_wishlist == "De tu lista de deseos"

    def test_engagement_with_review_likes_and_comments(self, feed_environment):
        engine = SmartFeedRankingEngine()
        obs = feed_environment['observer']
        friend = feed_environment['friend_mutual']
        book = feed_environment['book_favorite_genre']
        ctx = engine.build_user_context(obs)
        now = timezone.now()

        # Reseña con tracción (3 likes y 2 comentarios)
        rev_popular = Review.objects.create(
            user=friend,
            book=book,
            rating=10,
            title='Obra maestra imprescindible',
            text='Un análisis profundo y exhaustivo sobre la caída y renacimiento de la civilización galáctica...',
        )
        ReviewLike.objects.create(user=obs, review=rev_popular)
        ReviewComment.objects.create(user=obs, review=rev_popular, content='Completamente de acuerdo!')

        act_popular = Activity.objects.create(
            user=friend,
            type=ActivityType.REVIEW_CREATED,
            book=book,
            review=rev_popular,
        )
        act_popular.created_at = now - timedelta(hours=3)
        act_popular.save()

        # Simple BOOK_ADDED sin reseña ni tracción
        act_simple = Activity.objects.create(
            user=friend,
            type=ActivityType.BOOK_ADDED,
            book=book,
        )
        act_simple.created_at = now - timedelta(hours=3)
        act_simple.save()

        score_pop, sig_pop = engine.compute_score(act_popular, ctx, now=now)
        score_simple, _ = engine.compute_score(act_simple, ctx, now=now)

        assert score_pop > score_simple
        assert sig_pop in ("Reseña destacada", "Amistad mutua")

    def test_smart_ranking_reorders_higher_relevance_above_newer_low_affinity(self, feed_environment):
        """
        Una actividad de alta relevancia (amigo mutuo leyendo libro de tu wishlist)
        debe superar a una actividad 10 minutos más reciente pero de baja afinidad.
        """
        obs = feed_environment['observer']
        mutual = feed_environment['friend_mutual']
        casual = feed_environment['casual_follow']
        now = timezone.now()

        # Actividad A: casual follow añade un libro neutral hace 10 minutos (muy reciente pero irrelevante)
        act_low_affinity = Activity.objects.create(
            user=casual,
            type=ActivityType.BOOK_ADDED,
            book=feed_environment['book_neutral'],
        )
        act_low_affinity.created_at = now - timedelta(minutes=10)
        act_low_affinity.save()

        # Actividad B: amigo mutuo termina libro de tu lista de deseos hace 4 horas (alta afinidad y contenido)
        act_high_affinity = Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_FINISHED,
            book=feed_environment['book_wishlist'],
        )
        act_high_affinity.created_at = now - timedelta(hours=4)
        act_high_affinity.save()

        # En modo smart: B debe quedar en el primer puesto
        smart_ranked = get_smart_feed(obs, [act_low_affinity, act_high_affinity], mode='smart')
        assert smart_ranked[0].id == act_high_affinity.id
        assert smart_ranked[0].feed_signal == "De tu lista de deseos"

        # En modo cronológico: A debe quedar en primer puesto porque es más reciente
        chrono_ranked = get_smart_feed(obs, [act_low_affinity, act_high_affinity], mode='chronological')
        assert chrono_ranked[0].id == act_low_affinity.id


@pytest.mark.django_db
class TestSmartFeedAPIEndpoints:
    def test_api_feed_default_smart_mode(self, api_client, feed_environment):
        obs = feed_environment['observer']
        mutual = feed_environment['friend_mutual']
        now = timezone.now()

        act = Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_FINISHED,
            book=feed_environment['book_wishlist'],
        )
        act.created_at = now - timedelta(hours=1)
        act.save()

        api_client.force_authenticate(user=obs)
        res = api_client.get('/api/v1/users/feed/')
        assert res.status_code == 200
        data = res.json()

        assert 'results' in data
        assert len(data['results']) >= 1
        first_item = data['results'][0]
        assert 'score' in first_item
        assert 'feed_signal' in first_item
        assert 'timestamp' in first_item
        assert first_item['score'] is not None
        assert first_item['feed_signal'] is not None

    def test_api_feed_chronological_mode_parameter(self, api_client, feed_environment):
        obs = feed_environment['observer']
        mutual = feed_environment['friend_mutual']
        casual = feed_environment['casual_follow']
        now = timezone.now()

        act_older = Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_FINISHED,
            book=feed_environment['book_wishlist'],
        )
        Activity.objects.filter(id=act_older.id).update(created_at=now - timedelta(hours=3))

        act_newer = Activity.objects.create(
            user=casual,
            type=ActivityType.BOOK_ADDED,
            book=feed_environment['book_neutral'],
        )
        Activity.objects.filter(id=act_newer.id).update(created_at=now + timedelta(minutes=1))

        api_client.force_authenticate(user=obs)
        res = api_client.get('/api/v1/users/feed/?mode=chronological')
        assert res.status_code == 200
        results = res.json()['results']
        assert len(results) >= 2
        # El primero debe ser el más reciente por created_at
        assert results[0]['id'] == act_newer.id

    def test_api_feed_alias_books_feed(self, api_client, feed_environment):
        obs = feed_environment['observer']
        mutual = feed_environment['friend_mutual']
        Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_STARTED,
            book=feed_environment['book_favorite_genre'],
        )

        api_client.force_authenticate(user=obs)
        res = api_client.get('/api/v1/books/feed/')
        assert res.status_code == 200
        assert 'results' in res.json()
        assert len(res.json()['results']) >= 1

    def test_api_feed_type_filter(self, api_client, feed_environment):
        obs = feed_environment['observer']
        mutual = feed_environment['friend_mutual']

        Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_STARTED,
            book=feed_environment['book_favorite_genre'],
        )
        Activity.objects.create(
            user=mutual,
            type=ActivityType.BOOK_FINISHED,
            book=feed_environment['book_wishlist'],
        )

        api_client.force_authenticate(user=obs)
        res = api_client.get('/api/v1/users/feed/?type=BOOK_FINISHED')
        assert res.status_code == 200
        results = res.json()['results']
        for item in results:
            assert item['type'] == 'BOOK_FINISHED'

    def test_api_feed_excludes_blocked_users(self, api_client, feed_environment):
        obs = feed_environment['observer']
        blocked = feed_environment['blocked_user']

        Activity.objects.create(
            user=blocked,
            type=ActivityType.BOOK_FINISHED,
            book=feed_environment['book_neutral'],
        )

        api_client.force_authenticate(user=obs)
        res = api_client.get('/api/v1/users/feed/')
        assert res.status_code == 200
        user_ids = [item['user']['id'] for item in res.json()['results']]
        assert blocked.id not in user_ids

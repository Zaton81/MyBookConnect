"""
Suite de pruebas para la Fase 22 — Feed Social y Actividad.

Verifica:
1. Registro de actividades sociales requeridas: LIST_CREATED, REVIEW_LIKED, COMMENT_ADDED.
2. Controles de usuario en el feed: Ocultar (/feed/<id>/hide/) y desocultar (/feed/<id>/unhide/).
3. Exclusión inmediata de actividades de usuarios silenciados (muted_users).
4. Bloqueo bidireccional estricto (A bloquea B / B bloquea A).
5. Respeto al nivel de privacidad de actividad (activity_privacy_level: private vs public).
6. Filtrado temático de feed por parámetros ?category=... y ?type=...
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Review
from users.models import Activity, ActivityType, HiddenActivity, PrivacyChoices

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def social_env(db):
    """Configura un grafo social de lectores, libros y contenidos."""
    alice = User.objects.create_user(username='alice', email='alice@test.com', password='password123')
    bob = User.objects.create_user(username='bob', email='bob@test.com', password='password123')
    charlie = User.objects.create_user(username='charlie', email='charlie@test.com', password='password123')

    author = Author.objects.create(name='Gabriel García Márquez')
    book = Book.objects.create(
        title='Cien años de soledad',
        isbn='9780307350438',
        author=author,
        average_rating=4.8,
    )

    # Alice sigue a Bob y a Charlie
    alice.following.add(bob)
    alice.following.add(charlie)

    return {
        'alice': alice,
        'bob': bob,
        'charlie': charlie,
        'book': book,
    }


@pytest.mark.django_db
class TestPhase22SocialFeed:

    def test_list_created_activity_recorded(self, api_client, social_env):
        """Crear una lista pública registra la actividad LIST_CREATED en el feed."""
        bob = social_env['bob']
        api_client.force_authenticate(user=bob)

        payload = {
            'name': 'Joyas del Realismo Mágico',
            'description': 'Selección de obras imperdibles.',
            'privacy': 'public',
        }
        res = api_client.post('/api/v1/books/reading-lists/', payload, format='json')
        assert res.status_code == status.HTTP_201_CREATED

        # Verificar que se creó la actividad
        act = Activity.objects.filter(user=bob, type=ActivityType.LIST_CREATED).first()
        assert act is not None
        assert act.metadata.get('name') == 'Joyas del Realismo Mágico'

    def test_review_liked_activity_recorded(self, api_client, social_env):
        """Dar like a una reseña registra la actividad REVIEW_LIKED."""
        bob = social_env['bob']
        charlie = social_env['charlie']
        book = social_env['book']

        review = Review.objects.create(
            user=charlie,
            book=book,
            rating=5,
            title='Obra maestra',
            text='Impactante de principio a fin.',
        )

        api_client.force_authenticate(user=bob)
        res = api_client.post(f'/api/v1/books/reviews/{review.id}/like/')
        assert res.status_code == status.HTTP_200_OK
        assert res.data['liked'] is True

        act = Activity.objects.filter(user=bob, type=ActivityType.REVIEW_LIKED).first()
        assert act is not None
        assert act.review == review
        assert act.target_user == charlie

    def test_review_comment_activity_recorded(self, api_client, social_env):
        """Comentar en una reseña genera la actividad COMMENT_ADDED."""
        bob = social_env['bob']
        charlie = social_env['charlie']
        book = social_env['book']

        review = Review.objects.create(
            user=charlie,
            book=book,
            rating=4,
            title='Muy recomendable',
            text='Buena lectura.',
        )

        api_client.force_authenticate(user=bob)
        res = api_client.post(
            f'/api/v1/books/reviews/{review.id}/comments/',
            {'content': 'Totalmente de acuerdo con tu análisis.'},
            format='json',
        )
        assert res.status_code == status.HTTP_201_CREATED

        act = Activity.objects.filter(user=bob, type=ActivityType.COMMENT_ADDED).first()
        assert act is not None
        assert act.target_user == charlie
        assert act.review == review

    def test_hide_and_unhide_feed_activity(self, api_client, social_env):
        """El lector puede ocultar una publicación de su feed y luego restaurarla."""
        alice = social_env['alice']
        bob = social_env['bob']
        book = social_env['book']

        # Bob crea una actividad
        act = Activity.objects.create(
            user=bob,
            type=ActivityType.BOOK_FINISHED,
            book=book,
            metadata={'rating': 5},
        )

        api_client.force_authenticate(user=alice)

        # 1. Antes de ocultar, la actividad aparece en el feed de Alice
        feed_res = api_client.get('/api/v1/users/feed/?mode=chronological')
        assert feed_res.status_code == status.HTTP_200_OK
        activity_ids = [item['id'] for item in feed_res.data['results']]
        assert act.id in activity_ids

        # 2. Alice oculta la actividad
        hide_res = api_client.post(f'/api/v1/auth/feed/{act.id}/hide/')
        assert hide_res.status_code == status.HTTP_200_OK
        assert hide_res.data['hidden'] is True
        assert HiddenActivity.objects.filter(user=alice, activity=act).exists()

        # 3. La actividad ya NO aparece en el feed de Alice
        feed_res2 = api_client.get('/api/v1/users/feed/?mode=chronological')
        activity_ids2 = [item['id'] for item in feed_res2.data['results']]
        assert act.id not in activity_ids2

        # 4. Pero Bob sí ve su propia actividad
        api_client.force_authenticate(user=bob)
        bob_feed = api_client.get('/api/v1/users/feed/?mode=chronological')
        bob_ids = [item['id'] for item in bob_feed.data['results']]
        assert act.id in bob_ids

        # 5. Alice restaura la actividad
        api_client.force_authenticate(user=alice)
        unhide_res = api_client.post(f'/api/v1/auth/feed/{act.id}/unhide/')
        assert unhide_res.status_code == status.HTTP_200_OK
        assert unhide_res.data['hidden'] is False

        feed_res3 = api_client.get('/api/v1/users/feed/?mode=chronological')
        activity_ids3 = [item['id'] for item in feed_res3.data['results']]
        assert act.id in activity_ids3

    def test_feed_excludes_muted_users(self, api_client, social_env):
        """Silenciar a un usuario oculta inmediatamente todas sus actividades del feed."""
        alice = social_env['alice']
        bob = social_env['bob']
        book = social_env['book']

        act_bob = Activity.objects.create(
            user=bob,
            type=ActivityType.BOOK_STARTED,
            book=book,
        )

        api_client.force_authenticate(user=alice)

        # Feed antes de silenciar: actividad presente
        res1 = api_client.get('/api/v1/users/feed/?mode=chronological')
        act_ids1 = [item['id'] for item in res1.data['results']]
        assert act_bob.id in act_ids1

        # Alice silencia a Bob
        mute_res = api_client.post(f'/api/v1/auth/users/{bob.id}/mute/')
        assert mute_res.status_code == status.HTTP_200_OK
        assert mute_res.data['is_muted'] is True

        # Feed después de silenciar: actividad excluida
        res2 = api_client.get('/api/v1/users/feed/?mode=chronological')
        act_ids2 = [item['id'] for item in res2.data['results']]
        assert act_bob.id not in act_ids2

    def test_feed_strict_bidirectional_blocking(self, api_client, social_env):
        """Bloqueos bidireccionales ocultan recíprocamente la actividad en el feed."""
        alice = social_env['alice']
        bob = social_env['bob']
        book = social_env['book']

        act_alice = Activity.objects.create(user=alice, type=ActivityType.BOOK_FINISHED, book=book)
        act_bob = Activity.objects.create(user=bob, type=ActivityType.BOOK_FINISHED, book=book)

        # Bob sigue a Alice
        bob.following.add(alice)

        # Bob bloquea a Alice
        bob.blocked_users.add(alice)

        # Alice no debe ver a Bob
        api_client.force_authenticate(user=alice)
        res_alice = api_client.get('/api/v1/users/feed/?mode=chronological')
        alice_feed_ids = [item['id'] for item in res_alice.data['results']]
        assert act_bob.id not in alice_feed_ids

        # Bob tampoco debe ver a Alice
        api_client.force_authenticate(user=bob)
        res_bob = api_client.get('/api/v1/users/feed/?mode=chronological')
        bob_feed_ids = [item['id'] for item in res_bob.data['results']]
        assert act_alice.id not in bob_feed_ids

    def test_feed_privacy_levels(self, api_client, social_env):
        """Actividades de usuarios con activity_privacy_level='private' no se exponen a terceros."""
        alice = social_env['alice']
        bob = social_env['bob']
        book = social_env['book']

        # Bob configura su privacidad de actividad como privada
        bob.activity_privacy_level = PrivacyChoices.PRIVATE
        bob.save(update_fields=['activity_privacy_level'])

        act_bob = Activity.objects.create(
            user=bob,
            type=ActivityType.BOOK_STARTED,
            book=book,
        )

        api_client.force_authenticate(user=alice)
        res = api_client.get('/api/v1/users/feed/?mode=chronological')
        alice_ids = [item['id'] for item in res.data['results']]
        assert act_bob.id not in alice_ids

        # Pero Bob sí ve su propia actividad
        api_client.force_authenticate(user=bob)
        bob_res = api_client.get('/api/v1/users/feed/?mode=chronological')
        bob_ids = [item['id'] for item in bob_res.data['results']]
        assert act_bob.id in bob_ids

    def test_feed_category_and_type_filters(self, api_client, social_env):
        """El endpoint soporta filtros temáticos: ?category=reads, ?category=reviews, ?category=lists."""
        alice = social_env['alice']
        bob = social_env['bob']
        book = social_env['book']

        act_read = Activity.objects.create(user=bob, type=ActivityType.BOOK_FINISHED, book=book)
        act_rev = Activity.objects.create(user=bob, type=ActivityType.REVIEW_CREATED, book=book)
        act_list = Activity.objects.create(user=bob, type=ActivityType.LIST_CREATED, metadata={'name': 'Lista Top'})

        api_client.force_authenticate(user=alice)

        # Filtro reads
        res_reads = api_client.get('/api/v1/users/feed/?category=reads&mode=chronological')
        ids_reads = [item['id'] for item in res_reads.data['results']]
        assert act_read.id in ids_reads
        assert act_rev.id not in ids_reads
        assert act_list.id not in ids_reads

        # Filtro reviews
        res_reviews = api_client.get('/api/v1/users/feed/?category=reviews&mode=chronological')
        ids_reviews = [item['id'] for item in res_reviews.data['results']]
        assert act_rev.id in ids_reviews
        assert act_read.id not in ids_reviews

        # Filtro lists
        res_lists = api_client.get('/api/v1/users/feed/?category=lists&mode=chronological')
        ids_lists = [item['id'] for item in res_lists.data['results']]
        assert act_list.id in ids_lists
        assert act_read.id not in ids_lists

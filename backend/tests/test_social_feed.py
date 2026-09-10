from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, ReadingStatus, Review, UserBook
from books.services.cover_service import _is_valid_image
from users.models import Activity, ActivityType

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user_alice():
    return User.objects.create_user(username='alice', email='alice@example.com', password='password123')


@pytest.fixture
def user_bob():
    return User.objects.create_user(username='bob', email='bob@example.com', password='password123')


@pytest.fixture
def user_charlie():
    return User.objects.create_user(username='charlie', email='charlie@example.com', password='password123')


@pytest.fixture
def sample_book():
    author = Author.objects.create(name='Ursula K. Le Guin')
    return Book.objects.create(
        title='Los desposeídos',
        author=author,
        isbn='9788445070208',
        google_volume_id='abc123vol',
    )


@pytest.mark.django_db
class TestCoverSearchImprovements:
    def test_magic_bytes_detection(self):
        """Verifica que imágenes válidas se detecten incluso con content-type genérico o ausente."""
        jpeg_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        webp_bytes = b'RIFF\x00\x00\x00\x00WEBPVP8 '
        random_bytes = b'Hello world not an image'

        assert _is_valid_image(jpeg_bytes, 'application/octet-stream') is True
        assert _is_valid_image(png_bytes, '') is True
        assert _is_valid_image(webp_bytes, 'binary/octet-stream') is True
        assert _is_valid_image(random_bytes, 'text/plain') is False

    @patch('books.tasks.download_cover_task.delay')
    def test_search_enqueues_cover_download_for_uncovered_books(self, mock_delay, api_client, sample_book):
        """Al buscar libros, se programa la descarga en segundo plano para aquellos sin carátula."""
        cache.clear()
        assert not sample_book.cover

        res = api_client.get(f'/api/v1/books/?search={sample_book.title}')
        assert res.status_code == 200

        mock_delay.assert_called_with(sample_book.id)
        assert cache.get(f"bg_cover_search_{sample_book.id}") is True


@pytest.mark.django_db
class TestSocialFeedPhase18:
    def test_userbook_activities_emitted(self, user_alice, sample_book):
        """Crear y actualizar UserBook genera actividades BOOK_ADDED, BOOK_STARTED y BOOK_FINISHED."""
        # 1. Añadir a biblioteca
        ub = UserBook.objects.create(
            user=user_alice,
            book=sample_book,
            status=ReadingStatus.WANT_TO_READ,
        )
        assert Activity.objects.filter(user=user_alice, type=ActivityType.BOOK_ADDED, book=sample_book).exists()

        # 2. Empezar a leer
        ub.status = ReadingStatus.READING
        ub.progress = 25
        ub.save()
        assert Activity.objects.filter(user=user_alice, type=ActivityType.BOOK_STARTED, book=sample_book).exists()

        # 3. Terminar libro
        ub.status = ReadingStatus.READ
        ub.save()
        assert Activity.objects.filter(user=user_alice, type=ActivityType.BOOK_FINISHED, book=sample_book).exists()

    def test_review_activity_emitted(self, user_alice, sample_book):
        """Crear una reseña genera la actividad REVIEW_CREATED."""
        review = Review.objects.create(
            user=user_alice,
            book=sample_book,
            rating=10,
            title='Una utopía ambigua',
            text='Extraordinaria novela de ciencia ficción social.'
        )
        assert Activity.objects.filter(
            user=user_alice,
            type=ActivityType.REVIEW_CREATED,
            review=review,
            book=sample_book,
        ).exists()

    def test_follow_activity_emitted(self, api_client, user_alice, user_bob):
        """Seguir a un usuario genera la actividad USER_FOLLOWED."""
        api_client.force_authenticate(user=user_alice)
        res = api_client.post(f'/api/v1/users/{user_bob.id}/follow/')
        assert res.status_code == 200

        assert Activity.objects.filter(
            user=user_alice,
            type=ActivityType.USER_FOLLOWED,
            target_user=user_bob,
        ).exists()

    def test_feed_endpoint_following_activities(self, api_client, user_alice, user_bob, user_charlie, sample_book):
        """El feed del usuario muestra actividades de los seguidos y excluye a los no seguidos."""
        # Alice sigue a Bob, pero no a Charlie
        user_alice.following.add(user_bob)

        # Bob genera actividad
        Review.objects.create(
            user=user_bob,
            book=sample_book,
            rating=9,
            title='Gran libro de Bob',
        )

        # Charlie genera actividad (no debe verse por Alice)
        Review.objects.create(
            user=user_charlie,
            book=sample_book,
            rating=7,
            title='Reseña de Charlie',
        )

        api_client.force_authenticate(user=user_alice)
        res = api_client.get('/api/v1/users/feed/')
        assert res.status_code == 200

        activity_users = [item['user']['username'] for item in res.data['results']]
        assert 'bob' in activity_users
        assert 'charlie' not in activity_users

    def test_feed_endpoint_respects_blocked_users(self, api_client, user_alice, user_bob, sample_book):
        """Si un usuario bloquea a otro, sus actividades se ocultan inmediatamente del feed."""
        user_alice.following.add(user_bob)
        Review.objects.create(
            user=user_bob,
            book=sample_book,
            rating=8,
            title='Reseña pre-bloqueo',
        )

        # Alice bloquea a Bob
        user_alice.blocked_users.add(user_bob)

        api_client.force_authenticate(user=user_alice)
        res = api_client.get('/api/v1/users/feed/')
        assert res.status_code == 200

        activity_users = [item['user']['username'] for item in res.data['results']]
        assert 'bob' not in activity_users

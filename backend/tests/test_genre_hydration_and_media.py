from unittest.mock import patch
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework import status
from rest_framework.test import APIClient

from books.media_utils import build_media_url
from books.models import Author, Book, Category, Review, UserBook
from books.services.enrichment_service import enrich_book_metadata
from books.services.import_service import _create_or_get_from_volume

User = get_user_model()


@pytest.mark.django_db
class TestGenreHydrationAndMediaUrl:
    """Suite de pruebas para hidratación de géneros y URLs de medios."""

    def test_build_media_url_with_request(self):
        factory = RequestFactory()
        request = factory.get('/api/v1/books/')
        # Relative path
        url = build_media_url('/media/covers/test.jpg', request=request)
        assert url.startswith('http://testserver/media/covers/test.jpg')

        # None should return None
        assert build_media_url(None, request=request) is None

        # Absolute URL should remain intact
        assert build_media_url('https://images.com/cover.jpg', request=request) == 'https://images.com/cover.jpg'

    def test_build_media_url_with_media_base_url(self, monkeypatch):
        monkeypatch.setattr(settings, 'MEDIA_BASE_URL', 'https://cdn.mybookconnect.com')
        url = build_media_url('/media/covers/custom.jpg')
        assert url == 'https://cdn.mybookconnect.com/media/covers/custom.jpg'

    def test_create_or_get_from_volume_hydrates_categories(self):
        volume_payload = {
            'id': 'g_vol_12345',
            'volumeInfo': {
                'title': 'El resplandor',
                'authors': ['Stephen King'],
                'description': 'Novela de terror psicológico',
                'categories': ['Fiction / Thrillers / Suspense', 'Horror'],
                'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9780307743657'}],
            }
        }

        book = _create_or_get_from_volume(volume_payload)
        assert book.title == 'El resplandor'
        assert book.author.name == 'Stephen King'

        # Verificar que las categorías se crearon y asociaron
        cat_names = list(book.categories.values_list('name', flat=True))
        assert 'Fiction' in cat_names
        assert 'Thrillers' in cat_names
        assert 'Suspense' in cat_names
        assert 'Horror' in cat_names

    def test_enrich_book_metadata_hydrates_categories_and_synopsis(self):
        book = Book.objects.create(title='It', isbn='9781501142970')
        assert book.categories.count() == 0
        assert not book.description

        mock_gb_response = {
            'items': [{
                'volumeInfo': {
                    'description': 'A terrifying clown in Derry, Maine.',
                    'publishedDate': '1986-09-15',
                    'categories': ['Horror / Dark Fantasy'],
                }
            }]
        }

        with patch('requests.get') as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = mock_gb_response

            enrich_book_metadata(book)

        book.refresh_from_db()
        assert book.description == 'A terrifying clown in Derry, Maine.'
        cat_names = list(book.categories.values_list('name', flat=True))
        assert 'Horror' in cat_names
        assert 'Dark Fantasy' in cat_names

    def test_trending_and_social_feed_use_build_media_url(self):
        user = User.objects.create_user(username='lectora', password='password123')
        author = Author.objects.create(name='Isabel Allende')
        book = Book.objects.create(title='La casa de los espíritus', author=author, cover='covers/espiritus.jpg')
        Review.objects.create(user=user, book=book, rating=9, text='Excelente novela')
        UserBook.objects.create(user=user, book=book, is_read=True)

        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Trending books
        res_trending = client.get('/api/v1/books/trending/')
        assert res_trending.status_code == status.HTTP_200_OK
        trending_items = res_trending.data['results']
        assert len(trending_items) >= 1
        first_trending = trending_items[0]
        assert first_trending['cover'].startswith('http://testserver/media/covers/espiritus.jpg')

        # 2. Social Feed
        res_feed = client.get('/api/v1/books/feed/')
        assert res_feed.status_code == status.HTTP_200_OK
        feed_items = res_feed.data['results']
        assert len(feed_items) >= 1
        first_feed = feed_items[0]
        assert first_feed['book']['cover'].startswith('http://testserver/media/covers/espiritus.jpg')

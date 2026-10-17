from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
import pytest
from rest_framework.test import APIClient

from books.cache_utils import (
    book_detail_key,
    google_isbn_key,
    openlibrary_isbn_key,
    trending_key,
    wikipedia_book_key,
)
from books.models import Author, Book, Review, UserBook
from books.services.providers import (
    GoogleBooksProvider,
    OpenLibraryProvider,
    WikipediaProvider,
)

User = get_user_model()


@pytest.mark.django_db
class TestRedisCachingStrategy:
    @pytest.fixture(autouse=True)
    def clear_cache_before_each(self):
        cache.clear()
        yield
        cache.clear()

    def test_book_detail_cached_and_served_from_cache(self):
        author = Author.objects.create(name='Gabriel García Márquez')
        book = Book.objects.create(
            title='Cien años de soledad',
            author=author,
            enrichment_attempted=True,
            isbn='9780307474728',
        )

        client = APIClient()
        key = book_detail_key(book.id)
        assert cache.get(key) is None

        # Primera petición: se almacena en caché
        res1 = client.get(f'/api/v1/books/{book.id}/')
        assert res1.status_code == 200
        cached_data = cache.get(key)
        assert cached_data is not None
        assert cached_data['title'] == 'Cien años de soledad'

        # Modificar directamente en base de datos sin disparar señales
        Book.objects.filter(id=book.id).update(title='Título en BD cambiado')

        # Segunda petición: debe seguir sirviendo el contenido cacheado
        res2 = client.get(f'/api/v1/books/{book.id}/')
        assert res2.status_code == 200
        assert res2.json()['title'] == 'Cien años de soledad'

    def test_book_detail_invalidation_on_book_save(self):
        author = Author.objects.create(name='Isabel Allende')
        book = Book.objects.create(title='Paula', author=author, enrichment_attempted=True)
        key = book_detail_key(book.id)

        # Poblar caché manualmente
        cache.set(key, {'title': 'Paula'}, timeout=600)
        assert cache.get(key) is not None

        # Al guardar el modelo Book se debe invalidar la clave
        book.title = 'Paula (Edición Aniversario)'
        book.save()
        assert cache.get(key) is None

    def test_book_detail_invalidation_on_review_or_rating(self):
        author = Author.objects.create(name='Julio Cortázar')
        book = Book.objects.create(title='Bestiario', author=author, enrichment_attempted=True)
        user = User.objects.create_user(username='lector1', email='l1@test.com', password='pwd')
        key = book_detail_key(book.id)

        cache.set(key, {'title': 'Bestiario'}, timeout=600)
        assert cache.get(key) is not None

        # Añadir reseña o calificación
        Review.objects.create(user=user, book=book, rating=5, text='Extraordinario')
        assert cache.get(key) is None

    def test_trending_books_cached(self):
        author = Author.objects.create(name='Jorge Luis Borges')
        book = Book.objects.create(title='El Aleph', author=author)
        user = User.objects.create_user(username='lector2', email='l2@test.com', password='pwd')
        UserBook.objects.create(user=user, book=book, rating=5)

        client = APIClient()
        client.force_authenticate(user=user)

        t_key = trending_key('week')
        assert cache.get(t_key) is None

        res1 = client.get('/api/v1/books/trending/')
        assert res1.status_code == 200
        assert cache.get(t_key) is not None
        assert len(cache.get(t_key)) >= 1

        # Probar también periodo all
        t_key_all = trending_key('all')
        res2 = client.get('/api/v1/books/trending/?period=all')
        assert res2.status_code == 200
        assert cache.get(t_key_all) is not None

    def test_google_books_provider_uses_cache(self):
        provider = GoogleBooksProvider()
        isbn = '9788415448006'
        cache_key = google_isbn_key(isbn)

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            'items': [
                {
                    'id': 'g_cache_test',
                    'volumeInfo': {
                        'title': 'Don Quijote de la Mancha',
                        'authors': ['Miguel de Cervantes'],
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': isbn}],
                    },
                }
            ]
        }

        with patch('requests.get', return_value=mock_resp) as mock_get:
            first = provider.get_by_isbn(isbn)
            assert first is not None
            assert first.title == 'Don Quijote de la Mancha'
            assert mock_get.call_count == 1
            assert cache.get(cache_key) is not None

            # La segunda consulta debe resolverse desde caché sin HTTP request
            second = provider.get_by_isbn(isbn)
            assert second is not None
            assert second.title == 'Don Quijote de la Mancha'
            assert mock_get.call_count == 1

    def test_openlibrary_provider_uses_cache(self):
        provider = OpenLibraryProvider()
        isbn = '9780140449136'
        cache_key = openlibrary_isbn_key(isbn)

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = {
            f'ISBN:{isbn}': {
                'title': 'Crime and Punishment',
                'authors': [{'name': 'Fyodor Dostoevsky'}],
            }
        }

        with patch('requests.get', return_value=mock_resp) as mock_get:
            first = provider.get_by_isbn(isbn)
            assert first is not None
            assert first.title == 'Crime and Punishment'
            assert mock_get.call_count == 1
            assert cache.get(cache_key) is not None

            # Segunda llamada usa caché
            second = provider.get_by_isbn(isbn)
            assert second is not None
            assert second.title == 'Crime and Punishment'
            assert mock_get.call_count == 1

    def test_wikipedia_provider_uses_cache(self):
        provider = WikipediaProvider()
        title = 'La metamorfosis'
        cache_key = wikipedia_book_key(title)

        mock_search = MagicMock(ok=True)
        mock_search.json.return_value = {
            'query': {'search': [{'title': 'La metamorfosis'}]}
        }
        mock_summary = MagicMock(ok=True)
        mock_summary.json.return_value = {
            'title': 'La metamorfosis',
            'description': 'novela de Franz Kafka',
            'extract': 'Una mañana tras un sueño intranquilo...',
        }

        def side_effect(url, **kwargs):
            if 'api.php' in url:
                return mock_search
            return mock_summary

        with patch('requests.get', side_effect=side_effect) as mock_get:
            res1 = provider.search_by_title(title)
            assert len(res1) == 1
            assert res1[0].title == 'La metamorfosis'
            initial_calls = mock_get.call_count
            assert cache.get(cache_key) is not None

            # Segunda llamada usa caché
            res2 = provider.search_by_title(title)
            assert len(res2) == 1
            assert res2[0].title == 'La metamorfosis'
            assert mock_get.call_count == initial_calls

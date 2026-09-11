from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from books.cache_utils import user_stats_key
from books.models import Author, Book, Category, ReadingStatus, Review, UserBook
from books.services.enrichment_service import enrich_book_metadata
from books.services.stats_service import get_user_reading_stats

User = get_user_model()


@pytest.mark.django_db
class TestPhase22ReadingStats:
    """Suite de pruebas para la Fase 22: Estadísticas de Lectura y Caché."""

    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(
            username='reader_user',
            email='reader@example.com',
            password='Password123!',
            privacy_level='public',
        )

    @pytest.fixture
    def sample_books(self):
        auth1 = Author.objects.create(name='Brandon Sanderson')
        auth2 = Author.objects.create(name='Gabriel García Márquez')

        cat_fantasy = Category.objects.create(name='Fantasía', slug='fantasia')
        cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='ciencia-ficcion')
        cat_realism = Category.objects.create(name='Realismo Mágico', slug='realismo-magico')

        b1 = Book.objects.create(title='El camino de los reyes', author=auth1, isbn='9788466657662')
        b1.categories.add(cat_fantasy)

        b2 = Book.objects.create(title='Palabras radiantes', author=auth1, isbn='9788466657679')
        b2.categories.add(cat_fantasy)

        b3 = Book.objects.create(title='Cien años de soledad', author=auth2, isbn='9788439732471')
        b3.categories.add(cat_realism)

        b4 = Book.objects.create(title='Dune', author=auth1, isbn='9788466353779')
        b4.categories.add(cat_scifi)

        return [b1, b2, b3, b4]

    def test_get_user_reading_stats_metrics(self, test_user, sample_books):
        b1, b2, b3, b4 = sample_books

        # b1: leído, 1000 páginas, valorado con 10
        UserBook.objects.create(
            user=test_user,
            book=b1,
            status=ReadingStatus.READ,
            is_read=True,
            current_page=1000,
            progress=100,
            finished_at=date(2026, 3, 15),
        )
        Review.objects.create(user=test_user, book=b1, rating=10, text='Excelente!')

        # b2: leído, 1200 páginas, valorado con 8
        UserBook.objects.create(
            user=test_user,
            book=b2,
            status=ReadingStatus.READ,
            is_read=True,
            current_page=1200,
            progress=100,
            finished_at=date(2026, 4, 20),
        )
        Review.objects.create(user=test_user, book=b2, rating=8, text='Muy bueno!')

        # b3: leyendo, página 150
        UserBook.objects.create(
            user=test_user,
            book=b3,
            status=ReadingStatus.READING,
            current_page=150,
            progress=30,
        )

        # b4: quiero leer / wishlist
        UserBook.objects.create(
            user=test_user,
            book=b4,
            status=ReadingStatus.WANT_TO_READ,
            wishlist=True,
        )

        stats = get_user_reading_stats(test_user.id)

        assert stats['total_books'] == 4
        assert stats['total_read'] == 2
        assert stats['currently_reading'] == 1
        assert stats['want_to_read'] == 1
        assert stats['abandoned'] == 0
        assert stats['total_pages_read'] == 2350
        assert stats['average_rating'] == 9.0  # (10 + 8) / 2
        assert stats['ratings_distribution'][10] == 1
        assert stats['ratings_distribution'][8] == 1
        assert stats['ratings_distribution'][5] == 0

        # Verificar top géneros
        top_genre_names = [g['name'] for g in stats['top_genres']]
        assert 'Fantasía' in top_genre_names

        # Verificar top autores
        top_author_names = [a['name'] for a in stats['top_authors']]
        assert 'Brandon Sanderson' in top_author_names

    def test_reading_stats_cache_and_invalidation(self, test_user, sample_books):
        b1, b2, _, _ = sample_books
        cache.delete(user_stats_key(test_user.id))

        ub1 = UserBook.objects.create(
            user=test_user,
            book=b1,
            status=ReadingStatus.READ,
            current_page=500,
        )

        # Primer cálculo guarda en caché
        stats1 = get_user_reading_stats(test_user.id)
        assert stats1['total_read'] == 1
        assert cache.get(user_stats_key(test_user.id)) is not None

        # Guardar un nuevo UserBook debe invalidar la caché
        ub2 = UserBook.objects.create(
            user=test_user,
            book=b2,
            status=ReadingStatus.READ,
            current_page=300,
        )
        assert cache.get(user_stats_key(test_user.id)) is None

        # Siguiente cálculo debe reflejar la actualización
        stats2 = get_user_reading_stats(test_user.id)
        assert stats2['total_read'] == 2
        assert stats2['total_pages_read'] == 800

        # Eliminar una entrada debe invalidar la caché
        ub2.delete()
        assert cache.get(user_stats_key(test_user.id)) is None
        stats3 = get_user_reading_stats(test_user.id)
        assert stats3['total_read'] == 1

    def test_reading_stats_view_authenticated(self, test_user, sample_books):
        client = APIClient()
        client.force_authenticate(user=test_user)

        b1 = sample_books[0]
        UserBook.objects.create(
            user=test_user,
            book=b1,
            status=ReadingStatus.READ,
            current_page=450,
        )

        response = client.get('/api/v1/books/statistics/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['total_read'] == 1
        assert data['total_pages_read'] == 450

    def test_reading_stats_view_privacy(self, test_user):
        client = APIClient()
        # Usuario anónimo sin user_id debe retornar 401
        res_anon = client.get('/api/v1/books/statistics/')
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED

        # Usuario privado
        private_user = User.objects.create_user(
            username='private_reader',
            email='priv@example.com',
            password='Password123!',
            privacy_level='private',
        )
        other_user = User.objects.create_user(
            username='stranger',
            email='stranger@example.com',
            password='Password123!',
        )
        client.force_authenticate(user=other_user)

        # Consultar usuario privado siendo un extraño debe retornar 403
        res_priv = client.get(f'/api/v1/books/statistics/?user_id={private_user.id}')
        assert res_priv.status_code == status.HTTP_403_FORBIDDEN

        # Consultar usuario público debe retornar 200
        res_pub = client.get(f'/api/v1/books/statistics/?user_id={test_user.id}')
        assert res_pub.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestProactiveAutoFill:
    """Suite de pruebas para el auto-relleno proactivo de libros y autores."""

    def test_enrich_book_metadata_fills_missing_author_and_description(self):
        # Libro que carece de autor y descripción
        book = Book.objects.create(title='Cien años de soledad', isbn='9788439732471')
        assert book.author is None
        assert not book.description
        assert not book.categories.exists()

        mock_google_resp = MagicMock()
        mock_google_resp.ok = True
        mock_google_resp.json.return_value = {
            'items': [
                {
                    'volumeInfo': {
                        'title': 'Cien años de soledad',
                        'authors': ['Gabriel García Márquez'],
                        'description': 'La obra cumbre del realismo mágico.',
                        'publishedDate': '1967-05-30',
                        'categories': ['Fiction / Classics', 'Magical Realism'],
                    }
                }
            ]
        }

        with patch('requests.get', return_value=mock_google_resp):
            enrich_book_metadata(book)

        book.refresh_from_db()
        assert book.author is not None
        assert book.author.name == 'Gabriel García Márquez'
        assert 'realismo mágico' in book.description.lower()
        assert book.published_date is not None
        assert book.categories.filter(name='Classics').exists()

    def test_book_detail_view_triggers_enrichment_when_missing_fields(self):
        cache.clear()
        book = Book.objects.create(title='Libro Incompleto')
        client = APIClient()

        with patch('books.tasks.enrich_book_task.delay') as mock_task:
            res = client.get(f'/api/v1/books/{book.id}/')
            assert res.status_code == status.HTTP_200_OK
            mock_task.assert_called_once_with(book.id)

    def test_author_detail_view_triggers_enrichment_when_missing_photo_or_bio(self):
        author = Author.objects.create(name='Isabel Allende')
        client = APIClient()

        with patch('books.services.maybe_enrich_author') as mock_enrich:
            res = client.get(f'/api/v1/books/authors/{author.id}/')
            assert res.status_code == status.HTTP_200_OK
            mock_enrich.assert_called_once()

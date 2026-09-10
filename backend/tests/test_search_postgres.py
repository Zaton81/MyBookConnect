from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, Category, Review

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user():
    return User.objects.create_user(username='searcher', email='searcher@example.com', password='password123')


@pytest.fixture
def sample_data():
    cache.clear()
    author1 = Author.objects.create(name='Gabriel García Márquez', biography='Escritor colombiano')
    author2 = Author.objects.create(name='Julio Cortázar', biography='Escritor argentino')

    cat_fic = Category.objects.create(name='Ficción', slug='ficcion')
    cat_cla = Category.objects.create(name='Clásicos', slug='clasicos')

    book1 = Book.objects.create(
        title='Cien años de soledad',
        author=author1,
        isbn='9788437604947',
        description='La historia de la familia Buendía a lo largo de siete generaciones en Macondo.'
    )
    book1.categories.add(cat_fic, cat_cla)

    book2 = Book.objects.create(
        title='Rayuela',
        author=author2,
        isbn='9788437604572',
        description='Novela vanguardista sobre Horacio Oliveira en París.'
    )
    book2.categories.add(cat_fic)

    book3 = Book.objects.create(
        title='El coronel no tiene quien le escriba',
        author=author1,
        isbn='9788437604954',
        description='Un viejo coronel espera su pensión.'
    )

    return {
        'author1': author1,
        'author2': author2,
        'book1': book1,
        'book2': book2,
        'book3': book3,
    }


@pytest.mark.django_db
class TestReviewCreationBugfix:
    def test_review_creation_with_book_field(self, api_client, auth_user, sample_data):
        """Verifica que enviar 'book' como clave en el payload crea la reseña correctamente."""
        api_client.force_authenticate(user=auth_user)
        book = sample_data['book1']

        response = api_client.post('/api/v1/books/reviews/', {
            'book': book.id,
            'rating': 9,
            'title': 'Obra maestra',
            'text': 'Un libro imprescindible.'
        }, format='json')

        assert response.status_code in (200, 201)
        assert Review.objects.filter(user=auth_user, book=book).exists()
        review = Review.objects.get(user=auth_user, book=book)
        assert review.rating == 9
        assert review.title == 'Obra maestra'

    def test_review_creation_with_book_id_field(self, api_client, auth_user, sample_data):
        """Verifica que enviar 'book_id' como clave en el payload crea la reseña correctamente."""
        api_client.force_authenticate(user=auth_user)
        book = sample_data['book2']

        response = api_client.post('/api/v1/books/reviews/', {
            'book_id': book.id,
            'rating': 8,
            'title': 'Excelente',
            'text': 'Lectura no lineal fantástica.'
        }, format='json')

        assert response.status_code in (200, 201)
        assert Review.objects.filter(user=auth_user, book=book).exists()
        review = Review.objects.get(user=auth_user, book=book)
        assert review.rating == 8

    def test_review_creation_missing_book_returns_400(self, api_client, auth_user):
        """Verifica que si no se proporciona ni 'book' ni 'book_id', devuelve 400 Bad Request."""
        api_client.force_authenticate(user=auth_user)
        response = api_client.post('/api/v1/books/reviews/', {
            'rating': 5,
            'title': 'Sin libro',
        }, format='json')
        assert response.status_code == 400
        assert 'book_id es requerido' in response.data['detail']


@pytest.mark.django_db
class TestBackgroundEnrichmentTasks:
    @patch('books.tasks.download_cover_task.delay')
    def test_book_detail_triggers_cover_download_when_missing(self, mock_delay, api_client, sample_data):
        """Al solicitar un libro sin portada, encola la tarea Celery download_cover_task."""
        cache.clear()
        book = sample_data['book1']
        assert not book.cover

        response = api_client.get(f'/api/v1/books/{book.id}/')
        assert response.status_code == 200

        mock_delay.assert_called_once_with(book.id)
        assert cache.get(f"bg_cover_search_{book.id}") is True

        # Segunda petición: no debe volver a llamar gracias al cooldown en cache
        mock_delay.reset_mock()
        api_client.get(f'/api/v1/books/{book.id}/')
        mock_delay.assert_not_called()

    @patch('books.tasks.import_books_by_author_task.delay')
    def test_author_detail_triggers_import_books_task(self, mock_delay, api_client, sample_data):
        """Al visitar la página de un autor, encola la búsqueda de libros de autor en segundo plano."""
        cache.clear()
        author = sample_data['author1']

        response = api_client.get(f'/api/v1/books/authors/{author.id}/')
        assert response.status_code == 200

        mock_delay.assert_called_once_with(author.name)
        assert cache.get(f"bg_author_books_{author.id}") is True

        # Segunda petición: cooldown en cache evita llamada duplicada
        mock_delay.reset_mock()
        api_client.get(f'/api/v1/books/authors/{author.id}/')
        mock_delay.assert_not_called()

    @patch('books.tasks.import_books_by_author_task.delay')
    def test_author_books_view_triggers_import_books_task(self, mock_delay, api_client, sample_data):
        """Al visitar el endpoint de libros del autor, encola importación en segundo plano."""
        cache.clear()
        author = sample_data['author2']

        response = api_client.get(f'/api/v1/books/authors/{author.id}/books/')
        assert response.status_code == 200

        mock_delay.assert_called_once_with(author.name)
        assert cache.get(f"bg_author_books_{author.id}") is True


@pytest.mark.django_db
class TestAdvancedPostgresSearch:
    def test_search_by_title_and_author(self, api_client, sample_data):
        """Búsqueda por título exacto o autor devuelve resultados relevantes."""
        # Búsqueda por título
        res1 = api_client.get('/api/v1/books/?q=soledad')
        assert res1.status_code == 200
        titles1 = [b['title'] for b in res1.data['results']]
        assert 'Cien años de soledad' in titles1

        # Búsqueda por autor
        res2 = api_client.get('/api/v1/books/?search=Cortazar')
        assert res2.status_code == 200
        titles2 = [b['title'] for b in res2.data['results']]
        assert 'Rayuela' in titles2

    def test_search_by_isbn(self, api_client, sample_data):
        """Búsqueda por ISBN devuelve el libro correspondiente."""
        res = api_client.get('/api/v1/books/?q=9788437604572')
        assert res.status_code == 200
        titles = [b['title'] for b in res.data['results']]
        assert 'Rayuela' in titles

    def test_search_trigram_typo_tolerance(self, api_client, sample_data):
        """Búsqueda con erratas leves (trigram similarity) encuentra el libro."""
        # Errata en 'soledad' -> 'soledd'
        res = api_client.get('/api/v1/books/?q=soledd')
        assert res.status_code == 200
        titles = [b['title'] for b in res.data['results']]
        assert 'Cien años de soledad' in titles

        # Errata en 'Cortazar' -> 'Cortzar'
        res_author = api_client.get('/api/v1/books/?q=Cortzar')
        assert res_author.status_code == 200
        results_author = [b['title'] for b in res_author.data['results']]
        assert 'Rayuela' in results_author

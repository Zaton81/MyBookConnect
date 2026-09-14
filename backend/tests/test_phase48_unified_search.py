from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from books.models import Author, Book, Category
from books.services.unified_search_service import UnifiedSearchEngine, unified_book_search
from books.tasks import generate_book_embedding_task

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_user():
    return User.objects.create_user(username='phase48_user', email='phase48@example.com', password='password123')


@pytest.fixture
def test_catalog():
    cache.clear()
    author1 = Author.objects.create(name='Gabriel García Márquez', biography='Escritor y periodista colombiano, premio Nobel.')
    author2 = Author.objects.create(name='Julio Cortázar', biography='Escritor, traductor e intelectual argentino.')
    author3 = Author.objects.create(name='Isaac Asimov', biography='Escritor y bioquímico prolífico de ciencia ficción.')

    cat_fic = Category.objects.create(name='Ficción', slug='ficcion')
    cat_scifi = Category.objects.create(name='Ciencia Ficción', slug='ciencia-ficcion')
    cat_cla = Category.objects.create(name='Clásicos', slug='clasicos')

    book1 = Book.objects.create(
        title='Cien años de soledad',
        author=author1,
        isbn='9788437604947',
        description='La saga épica de la familia Buendía en el pueblo mítico de Macondo.',
        average_rating=4.8,
        embedding=[0.12, 0.45, 0.88, 0.05],
    )
    book1.categories.add(cat_fic, cat_cla)

    book2 = Book.objects.create(
        title='Rayuela',
        author=author2,
        isbn='9788437604572',
        description='Novela vanguardista contranovela de Horacio Oliveira en París y Buenos Aires.',
        average_rating=4.3,
        embedding=[0.30, 0.70, 0.10, 0.50],
    )
    book2.categories.add(cat_fic)

    book3 = Book.objects.create(
        title='Fundación',
        author=author3,
        isbn='9788497599252',
        description='Hari Seldon y la psicohistoria en el imperio galáctico espacial.',
        average_rating=4.7,
        embedding=[0.85, 0.15, 0.35, 0.90],
    )
    book3.categories.add(cat_scifi)

    return {
        'author1': author1,
        'author2': author2,
        'author3': author3,
        'cat_fic': cat_fic,
        'cat_scifi': cat_scifi,
        'book1': book1,
        'book2': book2,
        'book3': book3,
    }


@pytest.mark.django_db
class TestUnifiedSearchEngineService:
    def test_textual_search_mode(self, test_catalog):
        engine = UnifiedSearchEngine(mode='text')
        items, total = engine.search(query='Macondo', auto_import=False)
        assert total >= 1
        top_book = items[0].book
        assert top_book.id == test_catalog['book1'].id
        assert items[0].text_score > 0

    def test_fuzzy_search_mode_typo_tolerance(self, test_catalog):
        engine = UnifiedSearchEngine(mode='fuzzy')
        # Errata deliberada: 'Cortzar' en vez de 'Cortázar'
        items, total = engine.search(query='Cortzar', auto_import=False)
        assert total >= 1
        matched_ids = [item.book.id for item in items]
        assert test_catalog['book2'].id in matched_ids
        top_item = next(i for i in items if i.book.id == test_catalog['book2'].id)
        assert top_item.fuzzy_score > 0

    def test_semantic_search_mode_with_embeddings(self, test_catalog):
        engine = UnifiedSearchEngine(mode='semantic')
        with patch('books.services.unified_search_service.get_embedding_for_text') as mock_emb:
            # Mock query embedding similar al de Fundación ([0.85, 0.15, 0.35, 0.90])
            mock_emb.return_value = [0.84, 0.16, 0.34, 0.89]
            items, total = engine.search(query='psicohistoria galaxia', auto_import=False)
            assert total >= 1
            assert items[0].book.id == test_catalog['book3'].id
            assert items[0].semantic_score > 0.8

    def test_hybrid_search_mode_combined_scoring(self, test_catalog):
        engine = UnifiedSearchEngine(mode='hybrid')
        items, total = engine.search(query='soledad', auto_import=False)
        assert total >= 1
        top_item = items[0]
        assert top_item.book.id == test_catalog['book1'].id
        assert top_item.unified_score > 0
        assert top_item.match_type in ('exact', 'hybrid')

    def test_search_category_and_min_rating_filters(self, test_catalog):
        engine = UnifiedSearchEngine(mode='hybrid')
        # Búsqueda con filtro de categoría 'Ciencia Ficción'
        items, total = engine.search(query='imperio', category='Ciencia Ficción', auto_import=False)
        assert total >= 1
        assert all(test_catalog['cat_scifi'] in item.book.categories.all() for item in items)

        # Búsqueda con filtro de calificación mínima alta
        items_rated, _ = engine.search(query='a', min_rating=4.5, auto_import=False)
        for item in items_rated:
            assert item.book.average_rating >= 4.5

    def test_search_queryset_returns_django_queryset_with_order(self, test_catalog):
        engine = UnifiedSearchEngine(mode='hybrid')
        qs = engine.search_queryset(query='soledad', auto_import=False)
        assert qs.count() >= 1
        first_book = qs.first()
        assert first_book.id == test_catalog['book1'].id
        # Verificar que select_related y prefetch_related funcionan sin error
        assert first_book.author.name == 'Gabriel García Márquez'


@pytest.mark.django_db
class TestUnifiedSearchEndpoint:
    def test_endpoint_returns_unified_results(self, api_client, test_catalog):
        response = api_client.get('/api/v1/books/search/?q=soledad&mode=hybrid')
        assert response.status_code == 200
        data = response.data
        assert data['query'] == 'soledad'
        assert data['mode'] == 'hybrid'
        assert data['total'] >= 1
        assert len(data['results']) >= 1

        first_res = data['results'][0]
        assert first_res['book']['title'] == 'Cien años de soledad'
        assert 'unified_score' in first_res
        assert 'match_type' in first_res
        assert 'scores' in first_res
        assert 'text_score' in first_res['scores']
        assert 'fuzzy_score' in first_res['scores']
        assert 'semantic_score' in first_res['scores']

    def test_endpoint_empty_query_returns_empty_list(self, api_client):
        response = api_client.get('/api/v1/books/search/?q=')
        assert response.status_code == 200
        data = response.data
        assert data['count'] == 0
        assert data['results'] == []

    def test_endpoint_filters_by_category_and_author(self, api_client, test_catalog):
        response = api_client.get('/api/v1/books/search/?q=vanguardista&author=Cortazar')
        assert response.status_code == 200
        titles = [r['book']['title'] for r in response.data['results']]
        assert 'Rayuela' in titles

    def test_endpoint_pagination(self, api_client, test_catalog):
        response = api_client.get('/api/v1/books/search/?q=a&page=1&page_size=1')
        assert response.status_code == 200
        assert response.data['page'] == 1
        assert response.data['page_size'] == 1
        assert len(response.data['results']) <= 1


@pytest.mark.django_db
class TestBackwardCompatibilityBooksList:
    def test_legacy_q_parameter(self, api_client, test_catalog):
        res = api_client.get('/api/v1/books/?q=soledad')
        assert res.status_code == 200
        titles = [b['title'] for b in res.data['results']]
        assert 'Cien años de soledad' in titles

    def test_legacy_search_parameter(self, api_client, test_catalog):
        res = api_client.get('/api/v1/books/?search=Cortazar')
        assert res.status_code == 200
        titles = [b['title'] for b in res.data['results']]
        assert 'Rayuela' in titles

    def test_legacy_typo_tolerance(self, api_client, test_catalog):
        res = api_client.get('/api/v1/books/?q=soledd')
        assert res.status_code == 200
        titles = [b['title'] for b in res.data['results']]
        assert 'Cien años de soledad' in titles


@pytest.mark.django_db
class TestCeleryEmbeddingTask:
    def test_generate_book_embedding_task(self, test_catalog):
        book = test_catalog['book2']
        book.embedding = None
        book.save(update_fields=['embedding'])

        with patch('ai.embeddings.get_embedding_for_text') as mock_emb:
            mock_emb.return_value = [0.11, 0.22, 0.33]
            generate_book_embedding_task(book.id)

            book.refresh_from_db()
            assert book.embedding == [0.11, 0.22, 0.33]

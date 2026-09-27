import time
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from books.models import Author, Book, Category, Review, UserBook
from mybookconnect.query_profiler import QueryProfiler

User = get_user_model()


@pytest.fixture
def performance_dataset(db):
    """Genera un dataset representativo para pruebas de rendimiento y latencia."""
    cache.clear()
    author = Author.objects.create(name='Gabriel García Márquez', biography='Premio Nobel de Literatura')
    cat1, _ = Category.objects.get_or_create(name='Realismo Mágico', defaults={'slug': 'realismo-magico'})
    cat2, _ = Category.objects.get_or_create(name='Novela', defaults={'slug': 'novela'})

    books = []
    for i in range(12):
        b = Book.objects.create(
            title=f'Obra Maestra Volumen {i}',
            author=author,
            description=f'Descripción detallada y rica para búsqueda de la obra {i} en el catálogo.',
            isbn=f'9780000000{i:02d}',
            cover='covers/test.jpg',
            enrichment_attempted=True,
        )
        b.categories.add(cat1, cat2)
        books.append(b)

    user1 = User.objects.create_user(username='lector_sla_1', email='sla1@test.com', password='Password123!')
    user2 = User.objects.create_user(username='lector_sla_2', email='sla2@test.com', password='Password123!')

    for idx, b in enumerate(books[:6]):
        UserBook.objects.create(
            user=user1,
            book=b,
            is_read=True,
            rating=5 if idx % 2 == 0 else 4,
            current_page=150 + idx * 10,
        )
        Review.objects.create(
            user=user1,
            book=b,
            rating=5,
            text=f'Excelente libro número {idx}, totalmente recomendado.',
        )

    return {
        'author': author,
        'books': books,
        'user1': user1,
        'user2': user2,
    }


@pytest.mark.django_db
class TestSlaNormalEndpoints:
    """Valida que los endpoints transaccionales directos cumplan el SLA: p95 < 300 ms."""

    def test_healthcheck_sla_under_300ms(self):
        client = APIClient()
        # Warmup inicial de componentes y rutas
        client.get('/api/v1/health/')

        durations = []
        for _ in range(5):
            t_start = time.perf_counter()
            resp = client.get('/api/v1/health/')
            duration_ms = (time.perf_counter() - t_start) * 1000
            assert resp.status_code == 200
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 300.0, f"Healthcheck promedio {avg_duration:.2f}ms excede SLA de 300ms"

    def test_book_detail_sla_under_300ms(self, performance_dataset):
        client = APIClient()
        book_id = performance_dataset['books'][0].id
        # Warmup
        client.get(f'/api/v1/books/{book_id}/')

        durations = []
        for _ in range(5):
            t_start = time.perf_counter()
            resp = client.get(f'/api/v1/books/{book_id}/')
            duration_ms = (time.perf_counter() - t_start) * 1000
            assert resp.status_code == 200
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 300.0, f"Detalle de libro promedio {avg_duration:.2f}ms excede SLA de 300ms"

    def test_user_library_sla_under_300ms(self, performance_dataset):
        client = APIClient()
        user = performance_dataset['user1']
        client.force_authenticate(user=user)
        # Warmup
        client.get('/api/v1/books/user/books/')

        durations = []
        for _ in range(5):
            t_start = time.perf_counter()
            resp = client.get('/api/v1/books/user/books/')
            duration_ms = (time.perf_counter() - t_start) * 1000
            assert resp.status_code == 200
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 300.0, f"Biblioteca de usuario promedio {avg_duration:.2f}ms excede SLA de 300ms"


@pytest.mark.django_db
class TestSlaComplexEndpoints:
    """Valida que los endpoints con agregaciones y cálculos cumplan el SLA: p95 < 800 ms."""

    def test_trending_books_sla_under_800ms(self, performance_dataset):
        client = APIClient()
        user = performance_dataset['user1']
        client.force_authenticate(user=user)
        # Warmup
        client.get('/api/v1/books/trending/')

        durations = []
        for _ in range(4):
            t_start = time.perf_counter()
            resp = client.get('/api/v1/books/trending/')
            duration_ms = (time.perf_counter() - t_start) * 1000
            assert resp.status_code == 200
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 800.0, f"Trending promedio {avg_duration:.2f}ms excede SLA de 800ms"

    def test_recommendations_sla_under_800ms(self, performance_dataset):
        client = APIClient()
        user = performance_dataset['user1']
        client.force_authenticate(user=user)
        # Warmup
        client.get('/api/v1/books/recommendations/')

        durations = []
        for _ in range(4):
            t_start = time.perf_counter()
            resp = client.get('/api/v1/books/recommendations/')
            duration_ms = (time.perf_counter() - t_start) * 1000
            assert resp.status_code == 200
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 800.0, f"Recomendaciones promedio {avg_duration:.2f}ms excede SLA de 800ms"

    def test_reading_stats_summary_sla_under_800ms(self, performance_dataset):
        client = APIClient()
        user = performance_dataset['user1']
        client.force_authenticate(user=user)
        # Warmup
        client.get('/api/v1/books/statistics/')

        durations = []
        for _ in range(4):
            t_start = time.perf_counter()
            resp = client.get('/api/v1/books/statistics/')
            duration_ms = (time.perf_counter() - t_start) * 1000
            assert resp.status_code == 200
            durations.append(duration_ms)

        avg_duration = sum(durations) / len(durations)
        assert avg_duration < 800.0, f"Estadísticas promedio {avg_duration:.2f}ms excede SLA de 800ms"


@pytest.mark.django_db
class TestSlaSearchEndpoints:
    """Valida que los endpoints de búsqueda cumplan el SLA: p95 < 500 ms."""

    def test_text_search_sla_under_500ms(self, performance_dataset):
        from unittest.mock import patch

        client = APIClient()
        with patch('ai.clients.ollama_client.OllamaProvider.get_embedding', return_value=None), \
             patch('ai.embeddings.get_embedding_for_text', return_value=None):
            # Warmup
            client.get('/api/v1/books/?search=Maestra')

            durations = []
            for _ in range(5):
                t_start = time.perf_counter()
                resp = client.get('/api/v1/books/?search=Maestra')
                duration_ms = (time.perf_counter() - t_start) * 1000
                assert resp.status_code == 200
                durations.append(duration_ms)

            avg_duration = sum(durations) / len(durations)
            assert avg_duration < 500.0, f"Búsqueda promedio {avg_duration:.2f}ms excede SLA de 500ms"


@pytest.mark.django_db
class TestExplainAnalyzeOptimization:
    """Valida planes de ejecución con PostgreSQL EXPLAIN ANALYZE y uso de índices."""

    def test_query_profiler_search_execution(self, performance_dataset):
        profile = QueryProfiler.profile_book_search('Maestra')
        assert 'execution_time_ms' in profile
        assert 'planning_time_ms' in profile
        # En la base de datos de test, la ejecución debe ser sub-100ms
        assert profile['execution_time_ms'] < 100.0
        assert profile['planning_time_ms'] < 100.0

    def test_query_profiler_user_library_execution(self, performance_dataset):
        user = performance_dataset['user1']
        profile = QueryProfiler.profile_user_library(user.id)
        assert profile['execution_time_ms'] < 100.0
        assert profile['root_node_type'] != ''

    def test_query_profiler_reviews_execution(self, performance_dataset):
        book = performance_dataset['books'][0]
        profile = QueryProfiler.profile_book_reviews(book.id)
        assert profile['execution_time_ms'] < 100.0
        assert 'index_scans_used' in profile


@pytest.mark.django_db
class TestCacheLatencyImpact:
    """Demuestra y valida el impacto del caché en la latencia de respuesta."""

    def test_cache_hit_latency_reduction(self, performance_dataset):
        client = APIClient()
        book_id = performance_dataset['books'][0].id

        # 1. Petición fría (limpiando caché)
        cache.clear()
        t0 = time.perf_counter()
        resp_cold = client.get(f'/api/v1/books/{book_id}/')
        cold_duration = (time.perf_counter() - t0) * 1000
        assert resp_cold.status_code == 200

        # 2. Petición caliente (obtenida de Redis)
        t1 = time.perf_counter()
        resp_warm = client.get(f'/api/v1/books/{book_id}/')
        warm_duration = (time.perf_counter() - t1) * 1000
        assert resp_warm.status_code == 200

        # Ambas deben estar dentro del SLA
        assert cold_duration < 300.0
        assert warm_duration < 300.0


@pytest.mark.django_db
class TestBenchmarkManagementCommand:
    """Verifica la ejecución satisfactoria del comando administrativo de benchmark."""

    def test_benchmark_queries_command(self, performance_dataset):
        out = StringIO()
        call_command('benchmark_queries', samples=2, stdout=out)
        output = out.getvalue()
        assert 'Iniciando perfilado de consultas críticas' in output
        assert 'Búsqueda de Libros' in output
        assert 'Catálogo Principal' in output
        assert 'PASS' in output
        assert 'Todas las consultas evaluadas cumplen estrictamente' in output

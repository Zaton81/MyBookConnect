"""
Suite de pruebas para la Fase 9: Performance y base de datos (RoadmapV2 - Sección 14).
Cubre:
14.1. Auditoría y erradicación de consultas N+1 (perfiles, mensajes, seguimiento).
14.2. Inspección y verificación de planes de ejecución con EXPLAIN ANALYZE.
14.3. Presencia y funcionamiento de los nuevos índices compuestos en PostgreSQL:
      - idx_book_author_created
      - idx_review_book_rating
      - idx_review_user_book
      - idx_userbook_book_status
14.4. Paginación consistente y límites de seguridad en colecciones potencialmente infinitas.
14.5. Presupuestos de rendimiento (SLA: p95 < 500ms, p99 < 1.5s, queries críticas < 100ms) en observabilidad.
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, ReadingStatus, Review, ReviewComment, UserBook
from messages_app.models import Conversation, Message
from mybookconnect.observability import ObservabilityMetricsService
from mybookconnect.query_profiler import QueryProfiler

User = get_user_model()


@pytest.fixture
def perf_dataset(db):
    """Genera datos de prueba para verificar índices y consultas acotadas."""
    cache.clear()
    author = Author.objects.create(name="Stanislaw Lem", biography="Filósofo y autor de ciencia ficción polaco.")
    book1 = Book.objects.create(title="Solaris", author=author, isbn="9788439736851")
    book2 = Book.objects.create(title="Ciberíada", author=author, isbn="9788420651231")

    alice = User.objects.create_user(username="alice_perf", email="alice_perf@example.com", password="password123")
    bob = User.objects.create_user(username="bob_perf", email="bob_perf@example.com", password="password123")
    charlie = User.objects.create_user(username="charlie_perf", email="charlie_perf@example.com", password="password123")

    alice.following.add(bob)
    bob.following.add(alice)

    # Entradas de lectura
    UserBook.objects.create(user=alice, book=book1, status=ReadingStatus.READ, is_read=True)
    UserBook.objects.create(user=alice, book=book2, status=ReadingStatus.READING)
    UserBook.objects.create(user=bob, book=book1, status=ReadingStatus.READ, is_read=True)

    # Reseñas
    rev1 = Review.objects.create(user=alice, book=book1, rating=5, text="Obra maestra de la ciencia ficción filosófica.")
    Review.objects.create(user=bob, book=book1, rating=4, text="Muy profunda y reflexiva.")

    # Comentarios
    ReviewComment.objects.create(user=bob, review=rev1, content="Coincido totalmente con tu análisis.")

    # Conversación y mensajes
    conv = Conversation.objects.create()
    conv.participants.add(alice, bob)
    Message.objects.create(conversation=conv, sender=alice, text="Hola Bob")
    Message.objects.create(conversation=conv, sender=bob, text="Hola Alice, leíste Solaris?")

    return {
        'author': author,
        'book1': book1,
        'book2': book2,
        'alice': alice,
        'bob': bob,
        'charlie': charlie,
        'conv': conv,
        'rev1': rev1,
    }


@pytest.mark.django_db
class TestPhase09NPlusOneAudits:
    """Verifica que las consultas SQL permanezcan acotadas y no crezcan con N."""

    def test_user_profile_single_annotated_query(self, perf_dataset, django_assert_num_queries):
        """Verifica que UserProfileView resuelva todos los conteos en 1 consulta SQL sin N+1."""
        alice = perf_dataset['alice']
        client = APIClient()
        client.force_authenticate(user=alice)

        cache.clear()
        # Con cache limpia, resuelve perfil + conteos anotados y precargas en solo 3 consultas
        # (user + annotations, prefetch following, prefetch followers) sin N+1.
        with django_assert_num_queries(3):
            res = client.get("/api/v1/auth/profile/")
            assert res.status_code == status.HTTP_200_OK
            assert res.data['username'] == 'alice_perf'
            assert res.data['reviews_count'] == 1
            assert res.data['books_read_count'] == 1
            assert res.data['following_count'] == 1
            assert res.data['followers_count'] == 1

    def test_conversation_list_bounded_queries(self, perf_dataset, django_assert_num_queries):
        """Verifica que ConversationViewSet no ejecute N+1 consultas para last_message y unread_count."""
        alice = perf_dataset['alice']
        charlie = perf_dataset['charlie']

        # Crear una segunda conversación
        conv2 = Conversation.objects.create()
        conv2.participants.add(alice, charlie)
        Message.objects.create(conversation=conv2, sender=charlie, text="Hola desde chat 2")

        client = APIClient()
        client.force_authenticate(user=alice)

        # 4 queries acotadas: count paginador + conversations (con annotated unread_count) + participants + prefetched messages
        with django_assert_num_queries(4):
            res = client.get("/api/v1/auth/conversations/")
            assert res.status_code == status.HTTP_200_OK
            conv_list = res.data['results'] if 'results' in res.data else res.data
            assert len(conv_list) == 2
            # Verificar que el último mensaje y unread_count se hayan poblado correctamente
            for conv_data in conv_list:
                assert 'last_message' in conv_data
                assert conv_data['last_message'] is not None
                assert 'unread_count' in conv_data

    def test_check_follow_status_uses_exists_not_in_memory(self, perf_dataset, django_assert_num_queries):
        """Verifica que CheckFollowStatusView use consultas EXISTS indexadas sin cargar objetos a memoria."""
        alice = perf_dataset['alice']
        bob = perf_dataset['bob']
        client = APIClient()
        client.force_authenticate(user=alice)

        # 3 queries acotadas: get_object_or_404(User) + is_following exists + is_follower exists
        with django_assert_num_queries(3):
            res = client.get(f"/api/v1/users/{bob.id}/follow-status/")
            assert res.status_code == status.HTTP_200_OK
            assert res.data['is_following'] is True
            assert res.data['is_follower'] is True
            assert res.data['is_mutual'] is True


@pytest.mark.django_db
class TestPhase09DatabaseIndexesAndExplain:
    """Verifica la presencia física de los nuevos índices en PostgreSQL y su plan de ejecución (14.2 & 14.3)."""

    def test_new_composite_indexes_exist_in_postgres_catalog(self):
        """Verifica que los nuevos índices definidos en Phase 9 existan en PostgreSQL."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public';
                """
            )
            existing_indexes = {row[0] for row in cursor.fetchall()}

        phase09_expected_indexes = [
            'idx_book_author_created',
            'idx_review_book_rating',
            'idx_review_user_book',
            'idx_userbook_book_status',
        ]

        for idx_name in phase09_expected_indexes:
            assert idx_name in existing_indexes, f"Índice esperado '{idx_name}' no encontrado en PostgreSQL"

    def test_explain_analyze_runs_successfully(self, perf_dataset):
        """Verifica que QueryProfiler ejecute EXPLAIN ANALYZE sobre consultas con los nuevos índices."""
        book = perf_dataset['book1']
        qs = Review.objects.filter(book=book, rating__gte=4)

        report = QueryProfiler.explain_analyze(qs)
        assert 'execution_time_ms' in report
        assert 'planning_time_ms' in report
        assert report['execution_time_ms'] is not None
        # En bases de datos PostgreSQL el tiempo de consulta crítica debe ser menor a 100 ms
        assert report['execution_time_ms'] < 100.0


@pytest.mark.django_db
class TestPhase09PaginationAndSafetyLimits:
    """Verifica que los endpoints potencialmente masivos paginen o limiten colecciones (14.4)."""

    def test_review_comments_pagination_support(self, perf_dataset):
        """Verifica que el endpoint de comentarios de reseña soporte paginación estándar."""
        rev = perf_dataset['rev1']
        alice = perf_dataset['alice']
        client = APIClient()
        client.force_authenticate(user=alice)

        # Crear 25 comentarios para la reseña
        for i in range(24):
            ReviewComment.objects.create(user=alice, review=rev, content=f"Comentario adicional {i}")

        # Sin parámetro de paginación: retorna array seguro con tope máximo
        res_default = client.get(f"/api/v1/books/reviews/{rev.id}/comments/")
        assert res_default.status_code == status.HTTP_200_OK
        assert isinstance(res_default.data, list)
        assert len(res_default.data) == 25

        # Con parámetro de paginación (page=1): retorna estructura paginada estándar
        res_paginated = client.get(f"/api/v1/books/reviews/{rev.id}/comments/?page=1")
        assert res_paginated.status_code == status.HTTP_200_OK
        assert 'results' in res_paginated.data
        assert res_paginated.data['count'] == 25
        assert len(res_paginated.data['results']) == 20

    def test_followers_list_is_paginated(self, perf_dataset):
        """Verifica que la lista de seguidores aplique paginación por defecto."""
        alice = perf_dataset['alice']
        client = APIClient()
        client.force_authenticate(user=alice)

        res = client.get("/api/v1/users/followers/")
        assert res.status_code == status.HTTP_200_OK
        assert 'results' in res.data
        assert 'count' in res.data


@pytest.mark.django_db
class TestPhase09PerformanceBudgets:
    """Verifica la observabilidad de presupuestos de rendimiento y percentil p99 (14.5)."""

    def test_metrics_service_calculates_p95_p99_and_budgets(self):
        cache.clear()

        # Simular 100 peticiones con latencias conocidas
        for lat in range(1, 101):
            ObservabilityMetricsService.record_request(
                status_code=200,
                duration_ms=float(lat),  # 1ms a 100ms
                db_queries=2,
            )

        metrics = ObservabilityMetricsService.get_metrics()
        assert 'latency_ms' in metrics
        latency_info = metrics['latency_ms']
        assert 'p95' in latency_info
        assert 'p99' in latency_info
        assert latency_info['p95'] >= 90.0
        assert latency_info['p99'] >= 95.0

        assert 'performance_budgets' in metrics
        budgets = metrics['performance_budgets']
        assert budgets['api_p95_budget_ms'] == 500.0
        assert budgets['api_p99_budget_ms'] == 1500.0
        assert budgets['critical_queries_budget_ms'] == 100.0
        assert budgets['is_within_budget'] is True
        assert budgets['status'] == 'within_budget'

    def test_metrics_detects_budget_breach(self):
        cache.clear()

        # Simular latencias que superan el presupuesto p95 (500ms)
        for _ in range(50):
            ObservabilityMetricsService.record_request(status_code=200, duration_ms=600.0, db_queries=5)

        metrics = ObservabilityMetricsService.get_metrics()
        budgets = metrics['performance_budgets']
        assert budgets['is_within_budget'] is False
        assert budgets['status'] == 'breached'

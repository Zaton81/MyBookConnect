"""
Test Suite — Fase B4: Escalabilidad Básica
=============================================================================
Pruebas exhaustivas para:
- B4.1: Colas Celery separadas (default, books, ai, recommendations, emails) y enrutamiento.
- B4.2: Enrutador PrimaryReplicaRouter de PostgreSQL (lecturas, escrituras, migraciones y fallback).
- B4.3: Configuración de Nginx upstream balanceado con algoritmo least_conn.
- B4.4: Estrategia de caché L2 e invalidación en cascada (cascade_review_invalidation).
- B4.5: Script de benchmarking concurrente y reporte de SLAs de latencia.
"""
import os
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import override_settings

from books.cache_utils import (
    book_detail_key,
    cascade_review_invalidation,
    invalidate_book_cache,
    trending_key,
)
from books.models import Book
from mybookconnect.db_routers import PrimaryReplicaRouter


ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _find_repo_file(rel_path: str) -> Path:
    candidates = [
        Path("/repo") / rel_path,
        Path("/app") / rel_path,
        ROOT_DIR / rel_path,
        Path(__file__).resolve().parent.parent / rel_path,
        Path(os.getcwd()) / rel_path,
        Path(os.getcwd()).parent / rel_path,
    ]
    if rel_path == "frontend/nginx.conf":
        candidates.extend([
            Path("/repo/frontend_nginx.conf"),
            Path("/app/frontend_nginx.conf"),
        ])
    elif rel_path == "frontend/nginx.ssl.conf.template":
        candidates.extend([
            Path("/repo/nginx.ssl.conf.template"),
            Path("/app/nginx.ssl.conf.template"),
        ])
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"No se encontró {rel_path} en los candidatos evaluados.")


class TestCeleryQueuesAndRouting:
    """Pruebas de la arquitectura de 5 colas Celery independientes."""

    def test_canonical_celery_queues_registered(self):
        queues = getattr(settings, "CELERY_TASK_QUEUES", {})
        expected_queues = {"default", "books", "ai", "recommendations", "emails"}

        assert expected_queues.issubset(set(queues.keys())), (
            f"Faltan colas en CELERY_TASK_QUEUES. Esperadas: {expected_queues}, Actuales: {set(queues.keys())}"
        )
        assert getattr(settings, "CELERY_TASK_DEFAULT_QUEUE", None) == "default"

    def test_critical_tasks_routed_to_specialized_queues(self):
        routes = getattr(settings, "CELERY_TASK_ROUTES", {})

        # Cola 'books'
        assert routes.get("books.tasks.enrich_book_task", {}).get("queue") == "books"
        assert routes.get("books.tasks.download_cover_task", {}).get("queue") == "books"
        assert routes.get("books.tasks.recalculate_book_rating_task", {}).get("queue") == "books"

        # Cola 'ai'
        assert routes.get("books.tasks.generate_book_embedding_task", {}).get("queue") == "ai"
        assert routes.get("books.tasks.batch_reindex_embeddings_task", {}).get("queue") == "ai"

        # Cola 'recommendations'
        assert routes.get("books.tasks.precompute_trending_task", {}).get("queue") == "recommendations"
        assert routes.get("books.tasks.precompute_user_recommendations_task", {}).get("queue") == "recommendations"

        # Cola 'emails'
        assert routes.get("users.tasks.send_transactional_email_task", {}).get("queue") == "emails"
        assert routes.get("users.tasks.send_notification_email_task", {}).get("queue") == "emails"

        # Cola 'default'
        assert routes.get("analytics.tasks.record_analytics_event_task", {}).get("queue") == "default"


class TestPrimaryReplicaRouter:
    """Pruebas del enrutador de base de datos Primary / Replica de PostgreSQL."""

    def test_writes_always_go_to_default_primary(self):
        router = PrimaryReplicaRouter()
        assert router.db_for_write(Book) == "default"

    def test_reads_fallback_to_default_when_no_replica(self):
        router = PrimaryReplicaRouter()
        with override_settings(DATABASES={"default": {}}):
            assert router.db_for_read(Book) == "default"

    def test_reads_routed_to_replica_when_configured(self):
        router = PrimaryReplicaRouter()
        with override_settings(DATABASES={"default": {}, "replica": {}}):
            assert router.db_for_read(Book) == "replica"

    def test_migrations_only_allowed_on_default(self):
        router = PrimaryReplicaRouter()
        assert router.allow_migrate("default", "books") is True
        assert router.allow_migrate("replica", "books") is False


class TestNginxUpstreamConfiguration:
    """Pruebas de la configuración Nginx de upstream balanceado."""

    def test_nginx_conf_defines_upstream_django_cluster_with_least_conn(self):
        nginx_conf = _find_repo_file("frontend/nginx.conf")
        content = nginx_conf.read_text(encoding="utf-8")

        assert "upstream django_cluster" in content
        assert "least_conn;" in content
        assert "backend:8000" in content

    def test_nginx_ssl_template_defines_upstream_django_cluster(self):
        nginx_ssl = _find_repo_file("frontend/nginx.ssl.conf.template")
        content = nginx_ssl.read_text(encoding="utf-8")

        assert "upstream django_cluster" in content
        assert "least_conn;" in content


class TestL2CacheAndCascadeInvalidation:
    """Pruebas de la invalidación en cascada de caché L2."""

    def test_invalidate_book_cache_clears_detail_and_trending(self):
        book_id = 999
        detail_k = book_detail_key(book_id)
        cache.set(detail_k, {"id": book_id, "title": "Cached Book"}, timeout=300)
        cache.set(trending_key("week"), [{"id": book_id}], timeout=300)

        invalidate_book_cache(book_id)

        assert cache.get(detail_k) is None
        assert cache.get(trending_key("week")) is None

    @patch("books.tasks.recalculate_book_rating_task.delay")
    def test_cascade_review_invalidation_triggers_reactive_flow(self, mock_recalc):
        book_id = 123
        user_id = 456

        cache.set(book_detail_key(book_id), "detail_data", timeout=300)
        cascade_review_invalidation(book_id, user_id)

        assert cache.get(book_detail_key(book_id)) is None
        mock_recalc.assert_called_once_with(book_id)


class TestLoadTestingAndSLAReport:
    """Pruebas del script de benchmarking y reporte formal de SLAs."""

    def test_load_test_benchmark_script_exists_and_supports_json(self):
        script_path = _find_repo_file("scripts/load_testing/load_test_benchmark.py")
        content = script_path.read_text(encoding="utf-8")

        assert "--output-json" in content
        assert "/health/live" in content
        assert "/health/ready" in content
        assert "/api/v1/books/" in content

    def test_load_test_sla_report_defines_latency_budgets(self):
        doc_path = _find_repo_file("docs/deployment/load_test_sla_report.md")
        content = doc_path.read_text(encoding="utf-8")

        assert "SLA p95 Objetivo" in content
        assert "/health/live" in content
        assert "/api/v1/books/" in content
        assert "least_conn" in content
        assert "PrimaryReplicaRouter" in content

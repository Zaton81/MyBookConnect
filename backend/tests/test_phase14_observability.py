"""
Test Suite — Fase 14: Observabilidad, Telemetría y Alertas
=============================================================================
Pruebas exhaustivas para:
- 19.1: Formato JSON de logs, campos obligatorios y sanitización estricta de secretos.
- 19.2: Métricas de backend (latencias p50/p95/p99, 4xx/5xx, DB, Redis, Celery, WS)
        y métricas de producto (DAU, WAU, MAU, retención, estanterías, reviews, chat).
- 19.3: Motor de evaluación de alertas operativas (5xx elevado, fallos de dependencias, backlog).
"""
import datetime
import json
import logging
from unittest.mock import MagicMock, patch
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mybookconnect.logging_formatters import (
    REDACTED_PLACEHOLDER,
    StructuredJsonFormatter,
    sanitize_sensitive_data,
)
from mybookconnect.observability import (
    ObservabilityMetricsService,
    ProductMetricsService,
    SystemAlertsEvaluator,
)

User = get_user_model()


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username='admin_obs',
        email='admin_obs@mybookconnect.local',
        password='AdminPassword123!',
    )
    return user


@pytest.fixture
def regular_user(db):
    user = User.objects.create_user(
        username='regular_obs',
        email='regular_obs@mybookconnect.local',
        password='UserPassword123!',
    )
    return user


class TestPhase14StructuredLogging:
    """19.1. Verificación de logs estructurados en JSON y sanitización de credenciales."""

    def test_json_formatter_includes_all_required_canonical_fields(self):
        """Valida que StructuredJsonFormatter produzca los 7 campos canónicos obligatorios."""
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/app/views.py",
            lineno=42,
            msg="Request processed successfully",
            args=(),
            exc_info=None,
        )
        # Asignar atributos canónicos del middleware
        record.request_id = "req-12345-abcde"
        record.user_id = 99
        record.method = "GET"
        record.path = "/api/v1/books/"
        record.status = 200
        record.duration = 45.2

        formatted = formatter.format(record)
        data = json.loads(formatted)

        # 7 campos obligatorios Fase 14 (19.1)
        assert "timestamp" in data
        assert data["request_id"] == "req-12345-abcde"
        assert data["user_id"] == 99
        assert data["method"] == "GET"
        assert data["path"] == "/api/v1/books/"
        assert data["status"] == 200
        assert data["duration"] == 45.2
        assert data["level"] == "INFO"

    def test_sanitization_masks_passwords_and_tokens_recursively(self):
        """Valida que ninguna contraseña, token o API key se filtre en estructuras de datos."""
        raw_payload = {
            "username": "lector_seguro",
            "password": "SuperSecretPassword123!",
            "confirm_password": "SuperSecretPassword123!",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "access_token": "secret_access_xyz",
            "refresh_token": "secret_refresh_xyz",
            "api_key": "live_key_9999",
            "headers": {
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI5OSJ9.abcdef1234567890",
                "X-Api-Key": "secret_key_header",
            },
            "nested_list": [
                {"pwd": "nested_password_123"},
                "Bearer secret_bearer_token_value",
            ],
            "public_field": "este_campo_es_visible",
        }

        sanitized = sanitize_sensitive_data(raw_payload)

        # Ningún secreto debe ser legible
        assert sanitized["password"] == REDACTED_PLACEHOLDER
        assert sanitized["confirm_password"] == REDACTED_PLACEHOLDER
        assert sanitized["token"] == REDACTED_PLACEHOLDER
        assert sanitized["access_token"] == REDACTED_PLACEHOLDER
        assert sanitized["refresh_token"] == REDACTED_PLACEHOLDER
        assert sanitized["api_key"] == REDACTED_PLACEHOLDER
        assert sanitized["headers"]["Authorization"] == "Bearer ***REDACTED***"
        assert sanitized["headers"]["X-Api-Key"] == REDACTED_PLACEHOLDER
        assert sanitized["nested_list"][0]["pwd"] == REDACTED_PLACEHOLDER
        assert sanitized["nested_list"][1] == "Bearer ***REDACTED***"
        # Campos públicos permanecen intactos
        assert sanitized["public_field"] == "este_campo_es_visible"

    def test_json_formatter_sanitizes_record_attributes(self):
        """El formateador JSON debe aplicar sanitización a atributos adicionales del log."""
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="/app/auth.py",
            lineno=88,
            msg="Login attempt with credentials",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-login-001"
        record.user_id = None
        record.method = "POST"
        record.path = "/api/v1/auth/token/"
        record.status = 401
        record.duration = 15.0
        # Atributos sensibles inyectados
        record.password = "PlainPasswordSecret!"
        record.auth_token = "Bearer secret123"

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data["password"] == REDACTED_PLACEHOLDER
        assert data["auth_token"] == "Bearer ***REDACTED***"


@pytest.mark.django_db
class TestPhase14BackendMetrics:
    """19.2. Verificación de métricas de backend."""

    def setup_method(self):
        cache.clear()
        for key in [
            "requests_total",
            "requests_5xx",
            "requests_4xx",
            "latency_samples",
            "db_queries_total",
            "db_latency_samples",
            "celery_failures_total",
            "ws_connections",
        ]:
            cache.delete(f"{ObservabilityMetricsService.METRICS_PREFIX}:{key}")

    def test_record_request_increments_and_samples_latency(self):
        """Registrar peticiones debe acumular contadores y calcular percentiles p50/p95/p99."""
        # Registrar ráfaga de peticiones
        for i in range(1, 101):
            ObservabilityMetricsService.record_request(
                status_code=200 if i <= 90 else (400 if i <= 98 else 500),
                duration_ms=float(i * 5),  # 5ms, 10ms, ..., 500ms
                db_queries=2,
            )

        metrics = ObservabilityMetricsService.get_metrics()
        reqs = metrics["requests"]
        lat = metrics["latency_ms"]

        assert reqs["total"] == 100
        assert reqs["status_5xx_count"] == 2
        assert reqs["status_5xx_rate_pct"] == 2.0
        assert reqs["status_4xx_count"] == 8
        assert reqs["status_4xx_rate_pct"] == 8.0

        # Percentiles
        assert lat["p50"] > 0
        assert lat["p95"] >= lat["p50"]
        assert lat["p99"] >= lat["p95"]

    def test_db_and_redis_latency_measurement(self):
        """Debe medir las latencias operativas de PostgreSQL y Redis."""
        db_lat = ObservabilityMetricsService.measure_db_latency()
        redis_lat = ObservabilityMetricsService.measure_redis_latency()

        assert db_lat >= 0.0
        assert redis_lat >= 0.0

        metrics = ObservabilityMetricsService.get_metrics()
        assert metrics["database"]["latency_ms"] >= 0.0
        assert metrics["database"]["status"] == "healthy"
        assert metrics["redis"]["latency_ms"] >= 0.0
        assert metrics["redis"]["status"] == "healthy"

    def test_celery_and_websocket_metrics(self):
        """Verifica el registro de fallos en Celery y fluctuación de conexiones WebSocket."""
        ObservabilityMetricsService.record_celery_failure("tasks.reindex_embeddings")
        ObservabilityMetricsService.record_celery_failure("tasks.reindex_embeddings")

        ObservabilityMetricsService.record_websocket_connection(+3)
        ObservabilityMetricsService.record_websocket_connection(-1)

        metrics = ObservabilityMetricsService.get_metrics()
        bg = metrics["background_and_integrations"]

        assert bg["celery_failures_total"] == 2
        assert bg["active_websocket_connections"] == 2


@pytest.mark.django_db
class TestPhase14ProductMetrics:
    """19.2. Verificación de métricas de producto y engagement."""

    def setup_method(self):
        cache.clear()

    def test_product_metrics_calculation(self, admin_user, regular_user):
        """Valida que DAU, WAU, MAU, estanterías, reseñas y mensajes sean calculados."""
        now = timezone.now()
        # Simular actividad reciente para DAU/WAU/MAU
        admin_user.last_login = now
        admin_user.save(update_fields=['last_login'])

        regular_user.last_login = now - datetime.timedelta(days=3)
        regular_user.save(update_fields=['last_login'])

        metrics = ProductMetricsService.get_product_metrics()

        assert metrics["total_users"] >= 2
        assert metrics["dau"] >= 1  # admin_user activo hoy
        assert metrics["wau"] >= 2  # ambos activos en últimos 7 días
        assert metrics["mau"] >= 2  # ambos activos en últimos 30 días
        assert "retention_rate_pct" in metrics
        assert "books_added" in metrics
        assert "reviews" in metrics
        assert "follows" in metrics
        assert "messages" in metrics
        assert "recommendation_interactions" in metrics


class TestPhase14SystemAlerts:
    """19.3. Verificación de motor de alertas operativas."""

    def test_alerts_evaluates_healthy_system(self):
        """Un sistema con parámetros normales no debe disparar alertas y reportar HEALTHY."""
        backend_metrics = {
            'requests': {'total': 100, 'status_5xx_rate_pct': 0.0, 'status_4xx_rate_pct': 1.0},
            'database': {'status': 'healthy', 'latency_ms': 2.5},
            'redis': {'status': 'healthy', 'latency_ms': 0.8},
            'background_and_integrations': {'celery_queue_depth': 5},
        }

        alerts_eval = SystemAlertsEvaluator.evaluate_alerts(backend_metrics)
        assert alerts_eval["overall_status"] == "HEALTHY"
        assert alerts_eval["active_alerts_count"] == 0

    def test_alerts_triggers_critical_on_high_5xx(self):
        """Si la tasa de 5xx supera el 1%, debe disparar alerta CRITICAL."""
        backend_metrics = {
            'requests': {'total': 100, 'status_5xx_rate_pct': 5.0, 'status_4xx_rate_pct': 0.0},
            'database': {'status': 'healthy'},
            'redis': {'status': 'healthy'},
            'background_and_integrations': {'celery_queue_depth': 0},
        }

        alerts_eval = SystemAlertsEvaluator.evaluate_alerts(backend_metrics)
        assert alerts_eval["overall_status"] == "CRITICAL"
        alert_ids = [a["id"] for a in alerts_eval["alerts"]]
        assert "high_5xx_rate" in alert_ids

    def test_alerts_triggers_critical_on_db_down(self):
        """Si PostgreSQL no está disponible, debe disparar alerta CRITICAL."""
        backend_metrics = {
            'requests': {'total': 50, 'status_5xx_rate_pct': 0.0, 'status_4xx_rate_pct': 0.0},
            'database': {'status': 'unhealthy'},
            'redis': {'status': 'healthy'},
            'background_and_integrations': {'celery_queue_depth': 0},
        }

        alerts_eval = SystemAlertsEvaluator.evaluate_alerts(backend_metrics)
        assert alerts_eval["overall_status"] == "CRITICAL"
        alert_ids = [a["id"] for a in alerts_eval["alerts"]]
        assert "db_unavailable" in alert_ids

    def test_alerts_triggers_warning_on_celery_backlog(self):
        """Si la cola de Celery supera 100 tareas, debe disparar advertencia y estado DEGRADED."""
        backend_metrics = {
            'requests': {'total': 50, 'status_5xx_rate_pct': 0.0, 'status_4xx_rate_pct': 0.0},
            'database': {'status': 'healthy'},
            'redis': {'status': 'healthy'},
            'background_and_integrations': {'celery_queue_depth': 150},
        }

        alerts_eval = SystemAlertsEvaluator.evaluate_alerts(backend_metrics)
        assert alerts_eval["overall_status"] in ["DEGRADED", "WARNING"]
        alert_ids = [a["id"] for a in alerts_eval["alerts"]]
        assert "celery_backlog" in alert_ids


@pytest.mark.django_db
class TestPhase14ObservabilityApiEndpoint:
    """Verificación de acceso y permisos del endpoint /api/v1/observability/metrics/."""

    def test_anonymous_user_denied(self, client):
        """Peticiones sin autenticación deben responder 401 Unauthorized."""
        response = client.get('/api/v1/observability/metrics/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_forbidden(self, client, regular_user):
        """Usuarios no administradores deben recibir 403 Forbidden."""
        client.force_authenticate(user=regular_user)
        response = client.get('/api/v1/observability/metrics/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_user_success_and_complete_payload(self, client, admin_user):
        """Usuarios administradores reciben 200 OK con métricas de backend, producto y alertas."""
        client.force_authenticate(user=admin_user)
        response = client.get('/api/v1/observability/metrics/')
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Verificar presencia de las 4 secciones clave
        assert "backend_metrics" in data
        assert "product_metrics" in data
        assert "system_alerts" in data
        assert "performance_budgets" in data

        # Validar métricas de backend
        assert "requests" in data["backend_metrics"]
        assert "latency_ms" in data["backend_metrics"]
        assert "database" in data["backend_metrics"]
        assert "redis" in data["backend_metrics"]

        # Validar métricas de producto
        assert "dau" in data["product_metrics"]
        assert "wau" in data["product_metrics"]
        assert "mau" in data["product_metrics"]
        assert "books_added" in data["product_metrics"]
        assert "reviews" in data["product_metrics"]

        # Validar alertas de salud
        assert "overall_status" in data["system_alerts"]
        assert "alerts" in data["system_alerts"]

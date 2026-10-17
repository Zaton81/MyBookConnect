"""
Test Suite — Fase B3: Observabilidad y Alertas
=============================================================================
Pruebas exhaustivas para:
- B3.1: Logs JSON estructurados y sanitización de credenciales/PII.
- B3.2: Agregación de métricas de sistema (latencia p50/p95/p99, presupuestos, DB, Redis).
- B3.3: Agregación de métricas de producto (DAU, WAU, MAU, retención, interacciones).
- B3.4: Motor de evaluación de alertas operativas (SystemAlertsEvaluator) y umbrales.
- B3.5: Comando administrativo de evaluación de alertas (evaluate_system_alerts).
- B3.6: Integración y hook de sanitización previa de Sentry (sentry_before_send).
"""
import io
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command

from books.models import Author, Book, Review
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
from mybookconnect.settings import sentry_before_send

User = get_user_model()


class TestStructuredLoggingAndSanitization:
    """Pruebas del sistema de logging estructurado y enmascaramiento de datos sensibles."""

    def test_structured_json_formatter_emits_valid_json_with_canonical_fields(self):
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name="mybookconnect.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Operación completada con éxito",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert "timestamp" in data
        assert data["level"] == "INFO"
        assert data["logger"] == "mybookconnect.test"
        assert data["message"] == "Operación completada con éxito"

    def test_sanitize_sensitive_data_masks_passwords_and_api_keys(self):
        sensitive_payload = {
            "username": "lector_seguro",
            "password": "SuperSecretPassword123!",
            "api_key": "mbc_live_998877665544332211",
            "nested": {
                "secret_token": "token_confidencial",
                "normal_field": "valor_publico",
            },
        }
        sanitized = sanitize_sensitive_data(sensitive_payload)

        assert sanitized["username"] == "lector_seguro"
        assert sanitized["password"] == REDACTED_PLACEHOLDER
        assert sanitized["api_key"] == REDACTED_PLACEHOLDER
        assert sanitized["nested"]["secret_token"] == REDACTED_PLACEHOLDER
        assert sanitized["nested"]["normal_field"] == "valor_publico"

    def test_sanitize_sensitive_data_masks_jwt_and_bearer_headers(self):
        headers_payload = {
            "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummyPayload.dummySignature",
            "custom_header": "application/json",
        }
        sanitized = sanitize_sensitive_data(headers_payload)
        assert sanitized["authorization"] == REDACTED_PLACEHOLDER
        assert sanitized["custom_header"] == "application/json"


class TestObservabilityAndSystemMetrics:
    """Pruebas del servicio de métricas operacionales de backend y presupuestos."""

    def test_record_request_tracks_latency_and_percentiles(self):
        # Resetear métricas para el test
        ObservabilityMetricsService.reset_metrics()

        # Grabar muestras controladas de latencia
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        for lat in latencies:
            ObservabilityMetricsService.record_request(status_code=200, duration_ms=lat)

        metrics = ObservabilityMetricsService.get_metrics()

        assert metrics["requests"]["total"] >= 10
        assert metrics["latency_ms"]["p50"] > 0
        assert metrics["latency_ms"]["p95"] >= metrics["latency_ms"]["p50"]
        assert metrics["performance_budgets"]["is_within_budget"] is True

    @patch("django.db.connection.cursor")
    def test_database_latency_and_health_reporting(self, mock_cursor):
        mock_cursor.return_value.__enter__.return_value.execute.return_value = None
        metrics = ObservabilityMetricsService.get_metrics()

        assert "database" in metrics
        assert metrics["database"]["status"] in ("healthy", "unhealthy")
        assert "latency_ms" in metrics["database"]


class TestProductMetricsService:
    """Pruebas del agregador de métricas de producto y engagement."""

    @pytest.mark.django_db
    def test_product_metrics_aggregation(self):
        from django.core.cache import cache
        cache.delete(ProductMetricsService.CACHE_KEY)

        user = User.objects.create_user(
            username="product_metrics_user",
            email="p_user@mybookconnect.local",
            password="StrongPassword123!",
        )
        author = Author.objects.create(name="Virginia Woolf")
        book = Book.objects.create(title="Al faro", author=author, isbn="9780156030380")
        Review.objects.create(user=user, book=book, title="Genial", text="Impresionante obra.", rating=5)

        metrics = ProductMetricsService.get_product_metrics()

        assert metrics["total_users"] >= 1
        assert metrics["reviews"] >= 1
        assert "dau" in metrics
        assert "retention_rate_pct" in metrics


class TestSystemAlertsEvaluator:
    """Pruebas de los 7 umbrales del evaluador de alertas del sistema."""

    def test_system_alerts_evaluator_healthy_state(self):
        healthy_backend = {
            "requests": {
                "total": 100,
                "status_5xx_rate_pct": 0.0,
                "status_4xx_rate_pct": 1.0,
            },
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "background_and_integrations": {"celery_queue_depth": 5},
        }
        res = SystemAlertsEvaluator.evaluate_alerts(healthy_backend)

        assert res["overall_status"] == "HEALTHY"
        assert len(res["alerts"]) == 0

    def test_system_alerts_evaluator_triggers_high_5xx_critical(self):
        failing_backend = {
            "requests": {
                "total": 50,
                "status_5xx_rate_pct": 4.5,
                "status_4xx_rate_pct": 0.0,
            },
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "background_and_integrations": {"celery_queue_depth": 0},
        }
        res = SystemAlertsEvaluator.evaluate_alerts(failing_backend)

        assert res["overall_status"] == "CRITICAL"
        assert any(a["id"] == "high_5xx_rate" for a in res["alerts"])

    def test_system_alerts_evaluator_triggers_db_unavailable_critical(self):
        failing_backend = {
            "requests": {"total": 10, "status_5xx_rate_pct": 0.0, "status_4xx_rate_pct": 0.0},
            "database": {"status": "unhealthy"},
            "redis": {"status": "healthy"},
            "background_and_integrations": {"celery_queue_depth": 0},
        }
        res = SystemAlertsEvaluator.evaluate_alerts(failing_backend)

        assert res["overall_status"] == "CRITICAL"
        assert any(a["id"] == "db_unavailable" for a in res["alerts"])

    def test_system_alerts_evaluator_triggers_celery_backlog_warning(self):
        failing_backend = {
            "requests": {"total": 10, "status_5xx_rate_pct": 0.0, "status_4xx_rate_pct": 0.0},
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "background_and_integrations": {"celery_queue_depth": 250},
        }
        res = SystemAlertsEvaluator.evaluate_alerts(failing_backend)

        assert res["overall_status"] == "DEGRADED"
        assert any(a["id"] == "celery_backlog" for a in res["alerts"])


class TestEvaluateSystemAlertsCommand:
    """Pruebas del comando django evaluate_system_alerts."""

    @pytest.fixture(autouse=True)
    def clean_metrics_state(self):
        from django.core.cache import cache
        ObservabilityMetricsService.reset_metrics()
        cache.delete(ProductMetricsService.CACHE_KEY)

    @pytest.mark.django_db
    def test_evaluate_system_alerts_json_mode(self):
        out = io.StringIO()
        call_command("evaluate_system_alerts", "--json", stdout=out)
        data = json.loads(out.getvalue())

        assert "status" in data
        assert "alerts_count" in data
        assert data["thresholds_evaluated"] == 7
        assert "system_summary" in data

    @patch("requests.post")
    @pytest.mark.django_db
    def test_evaluate_system_alerts_webhook_dispatch(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        out = io.StringIO()
        call_command(
            "evaluate_system_alerts",
            "--webhook-url=https://alertmanager.mybookconnect.local/webhook",
            "--json",
            stdout=out,
        )
        data = json.loads(out.getvalue())
        assert "status" in data


class TestSentryIntegrationAndSanitization:
    """Pruebas de la configuración y filtro preventivo before_send de Sentry."""

    def test_sentry_before_send_sanitizes_pii_and_auth_headers(self):
        event = {
            "request": {
                "data": {"password": "ConfidentialPassword123!", "username": "ana"},
                "headers": {"Authorization": "Bearer sensitive_token_xyz"},
                "cookies": {"sessionid": "secret_cookie_token"},
            },
            "extra": {"api_key": "api_key_secret_123"},
        }
        cleaned_event = sentry_before_send(event, hint={})

        assert cleaned_event["request"]["data"]["password"] == REDACTED_PLACEHOLDER
        assert cleaned_event["request"]["data"]["username"] == "ana"
        assert cleaned_event["request"]["headers"]["Authorization"] == f"Bearer {REDACTED_PLACEHOLDER}"
        assert cleaned_event["extra"]["api_key"] == REDACTED_PLACEHOLDER

    def test_sentry_settings_defined_in_django_settings(self):
        assert hasattr(settings, "SENTRY_DSN")
        assert hasattr(settings, "SENTRY_ENVIRONMENT")
        assert hasattr(settings, "SENTRY_TRACES_SAMPLE_RATE")
        assert hasattr(settings, "USE_STRUCTURED_LOGS")

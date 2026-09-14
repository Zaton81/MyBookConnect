import json
import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from rest_framework.test import APIClient

from mybookconnect.observability import (
    ObservabilityMetricsService,
    StructuredJsonFormatter,
    StructuredLoggingMiddleware,
    sanitize_sensitive_data,
)

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_cache():
    """Limpia la caché antes de cada prueba de observabilidad."""
    cache.clear()
    yield
    cache.clear()


class TestSanitizeSensitiveData:
    """Pruebas unitarias para la función de sanitización y ofuscación de credenciales."""

    def test_sanitize_dictionary_sensitive_keys(self):
        sensitive_data = {
            'username': 'antonio',
            'password': 'SuperSecretPassword123!',
            'access_token': 'secret_jwt_token_here',
            'refresh_token': 'secret_refresh_token',
            'api_key': 'secret-google-api-key',
            'client_secret': 'super-secret',
            'nested': {
                'authorization': 'Bearer confidential_token',
                'normal_field': 'public_info',
            },
        }

        sanitized = sanitize_sensitive_data(sensitive_data)

        assert sanitized['username'] == 'antonio'
        assert sanitized['password'] == '***REDACTED***'
        assert sanitized['access_token'] == '***REDACTED***'
        assert sanitized['refresh_token'] == '***REDACTED***'
        assert sanitized['api_key'] == '***REDACTED***'
        assert sanitized['client_secret'] == '***REDACTED***'
        assert sanitized['nested']['authorization'] == '***REDACTED***'
        assert sanitized['nested']['normal_field'] == 'public_info'

    def test_sanitize_bearer_token_string(self):
        auth_header = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0'
        sanitized = sanitize_sensitive_data(auth_header)
        assert sanitized == 'Bearer ***REDACTED***'

    def test_sanitize_list_of_items(self):
        items = [
            {'name': 'item1', 'token': 'abc'},
            {'name': 'item2', 'api_key': 'xyz'},
        ]
        sanitized = sanitize_sensitive_data(items)
        assert sanitized[0]['token'] == '***REDACTED***'
        assert sanitized[1]['api_key'] == '***REDACTED***'
        assert sanitized[0]['name'] == 'item1'


class TestStructuredJsonFormatter:
    """Pruebas unitarias para el formateador de logs estructurados en JSON."""

    def test_formatter_produces_valid_json_with_standard_fields(self):
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg='Test message %s',
            args=('hello',),
            exc_info=None,
        )
        record.request_id = 'test-request-uuid-123'
        record.user_id = 99

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data['logger'] == 'test_logger'
        assert data['level'] == 'INFO'
        assert data['message'] == 'Test message hello'
        assert data['request_id'] == 'test-request-uuid-123'
        assert data['user_id'] == 99
        assert 'timestamp' in data
        assert data['line'] == 42

    def test_formatter_redacts_sensitive_keys_in_extra(self):
        formatter = StructuredJsonFormatter()
        record = logging.LogRecord(
            name='security_logger',
            level=logging.WARNING,
            pathname=__file__,
            lineno=50,
            msg='User login attempt',
            args=(),
            exc_info=None,
        )
        record.password = 'super_secret'
        record.token = 'sensitive_token'
        record.safe_field = 'safe_value'

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert data['password'] == '***REDACTED***'
        assert data['token'] == '***REDACTED***'
        assert data['safe_field'] == 'safe_value'

    def test_formatter_captures_exception_traceback(self):
        formatter = StructuredJsonFormatter()
        try:
            raise ValueError('Test error explosion')
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name='error_logger',
            level=logging.ERROR,
            pathname=__file__,
            lineno=70,
            msg='Something went wrong',
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert 'exception' in data
        assert 'ValueError: Test error explosion' in data['exception']


class TestStructuredLoggingMiddleware:
    """Pruebas del middleware de trazabilidad distribuida e inyección de X-Request-ID."""

    def test_middleware_generates_request_id_if_missing(self):
        rf = RequestFactory()
        request = rf.get('/api/v1/books/')
        
        get_response = MagicMock(return_value=HttpResponse(status=200))
        middleware = StructuredLoggingMiddleware(get_response)

        response = middleware(request)

        assert hasattr(request, 'request_id')
        assert request.request_id is not None
        assert response.headers.get('X-Request-ID') == request.request_id

    def test_middleware_propagates_existing_request_id(self):
        rf = RequestFactory()
        custom_id = str(uuid.uuid4())
        request = rf.get('/api/v1/books/', HTTP_X_REQUEST_ID=custom_id)

        get_response = MagicMock(return_value=HttpResponse(status=200))
        middleware = StructuredLoggingMiddleware(get_response)

        response = middleware(request)

        assert request.request_id == custom_id
        assert response.headers.get('X-Request-ID') == custom_id

    def test_middleware_records_metrics_on_response(self):
        rf = RequestFactory()
        request = rf.get('/api/v1/test/')
        
        get_response = MagicMock(return_value=HttpResponse(status=200))
        middleware = StructuredLoggingMiddleware(get_response)

        with patch.object(ObservabilityMetricsService, 'record_request') as mock_record:
            middleware(request)
            mock_record.assert_called_once()
            call_kwargs = mock_record.call_args[1]
            assert call_kwargs['status_code'] == 200
            assert 'duration_ms' in call_kwargs

    def test_middleware_process_exception_logs_error(self):
        rf = RequestFactory()
        request = rf.get('/api/v1/error/')
        request.request_id = 'err-id-123'

        middleware = StructuredLoggingMiddleware(lambda r: None)
        exc = RuntimeError('Unhandled exception')

        with patch('mybookconnect.observability.logger.error') as mock_logger:
            middleware.process_exception(request, exc)
            mock_logger.assert_called_once()
            call_kwargs = mock_logger.call_args[1]
            assert call_kwargs['extra']['request_id'] == 'err-id-123'
            assert call_kwargs['extra']['error'] == 'Unhandled exception'


class TestObservabilityMetricsService:
    """Pruebas del servicio de agregación de métricas de salud y rendimiento."""

    def test_metrics_collection_and_percentages(self):
        # Registrar peticiones simuladas
        ObservabilityMetricsService.record_request(status_code=200, duration_ms=50.0, db_queries=2)
        ObservabilityMetricsService.record_request(status_code=200, duration_ms=100.0, db_queries=4)
        ObservabilityMetricsService.record_request(status_code=404, duration_ms=30.0, db_queries=1)
        ObservabilityMetricsService.record_request(status_code=500, duration_ms=120.0, db_queries=3)

        # Registrar fallos de Celery y proveedores externos
        ObservabilityMetricsService.record_celery_failure('tasks.import_books')
        ObservabilityMetricsService.record_external_provider_call('google_books', success=True, duration_ms=150.0)
        ObservabilityMetricsService.record_external_provider_call('openlibrary', success=False, duration_ms=250.0)
        ObservabilityMetricsService.record_websocket_connection(delta=5)
        ObservabilityMetricsService.record_websocket_connection(delta=-2)

        metrics = ObservabilityMetricsService.get_metrics()

        assert metrics['requests']['total'] == 4
        assert metrics['requests']['status_5xx_count'] == 1
        assert metrics['requests']['status_5xx_rate_pct'] == 25.0
        assert metrics['requests']['status_4xx_count'] == 1
        assert metrics['requests']['status_4xx_rate_pct'] == 25.0

        assert metrics['latency_ms']['sample_size'] == 4
        assert metrics['latency_ms']['average'] == 75.0
        assert metrics['latency_ms']['p95'] >= 100.0

        assert metrics['database']['total_queries'] == 10
        assert metrics['database']['avg_queries_per_request'] == 2.5

        assert metrics['background_and_integrations']['celery_failures_total'] == 1
        assert metrics['background_and_integrations']['external_api_errors_total'] == 1
        assert metrics['background_and_integrations']['active_websocket_connections'] == 3
        assert 'timestamp' in metrics


@pytest.mark.django_db
class TestObservabilityMetricsView:
    """Pruebas de la API de telemetría /api/v1/observability/metrics/."""

    def test_anonymous_user_cannot_access_metrics(self):
        client = APIClient()
        response = client.get('/api/v1/observability/metrics/')
        assert response.status_code == 401

    def test_regular_authenticated_user_forbidden(self):
        user = User.objects.create_user(
            username='regular_observer',
            email='observer@example.com',
            password='Password123!',
            is_staff=False,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get('/api/v1/observability/metrics/')
        assert response.status_code == 403

    def test_staff_admin_can_access_metrics(self):
        admin_user = User.objects.create_user(
            username='staff_observer',
            email='admin_observer@example.com',
            password='Password123!',
            is_staff=True,
        )
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Pre-poblar algunas métricas
        ObservabilityMetricsService.record_request(status_code=200, duration_ms=45.0, db_queries=3)

        response = client.get('/api/v1/observability/metrics/')
        assert response.status_code == 200
        data = response.json()

        assert 'requests' in data
        assert 'latency_ms' in data
        assert 'database' in data
        assert 'background_and_integrations' in data
        assert data['requests']['total'] >= 1

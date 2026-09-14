"""
Fase 42: Módulo de Observabilidad y Logging Estructurado.
Proporciona:
- StructuredJsonFormatter: Formateador JSON para observabilidad centralizada.
- sanitize_sensitive_data: Enmascaramiento de credenciales, tokens y secretos.
- StructuredLoggingMiddleware: Middleware HTTP para inyección de request_id,
  medición de latencia, conteo de consultas SQL y logging estructurado.
- ObservabilityMetricsService: Agregador de métricas (latencia, 5xx, consultas BD,
  fallos en Celery, errores en proveedores externos y WebSockets).
- ObservabilityMetricsView: Endpoint administrativo seguro (/api/v1/observability/metrics/).
"""
import datetime
import json
import logging
import re
import time
import uuid
from typing import Any, Dict

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .logging_formatters import (
    REDACTED_PLACEHOLDER,
    SENSITIVE_KEY_PATTERNS,
    StructuredJsonFormatter,
    sanitize_sensitive_data,
)

logger = logging.getLogger('mybookconnect.structured')


class ObservabilityMetricsService:
    """
    Servicio de agregación y cálculo de métricas de rendimiento y fiabilidad.
    Utiliza Redis con fallback en memoria para mantener contadores y latencias.
    """
    METRICS_PREFIX = 'mbc:metrics'
    MAX_LATENCY_SAMPLES = 200

    @classmethod
    def record_request(cls, status_code: int, duration_ms: float, db_queries: int = 0) -> None:
        """Registra una petición HTTP procesada con su código, duración y consultas SQL."""
        try:
            now = int(time.time())
            cache.incr(f"{cls.METRICS_PREFIX}:requests_total", 1)
        except Exception:
            # Si no existe la clave para incr, inicializar
            cache.set(f"{cls.METRICS_PREFIX}:requests_total", 1, timeout=86400)

        if status_code >= 500:
            try:
                cache.incr(f"{cls.METRICS_PREFIX}:requests_5xx", 1)
            except Exception:
                cache.set(f"{cls.METRICS_PREFIX}:requests_5xx", 1, timeout=86400)
        elif status_code >= 400:
            try:
                cache.incr(f"{cls.METRICS_PREFIX}:requests_4xx", 1)
            except Exception:
                cache.set(f"{cls.METRICS_PREFIX}:requests_4xx", 1, timeout=86400)

        # Muestreo circular de latencias en caché
        try:
            samples_key = f"{cls.METRICS_PREFIX}:latency_samples"
            samples = cache.get(samples_key) or []
            if not isinstance(samples, list):
                samples = []
            samples.append(duration_ms)
            if len(samples) > cls.MAX_LATENCY_SAMPLES:
                samples = samples[-cls.MAX_LATENCY_SAMPLES:]
            cache.set(samples_key, samples, timeout=3600)
        except Exception:
            pass

        # Total de consultas DB
        try:
            cache.incr(f"{cls.METRICS_PREFIX}:db_queries_total", db_queries)
        except Exception:
            cache.set(f"{cls.METRICS_PREFIX}:db_queries_total", db_queries, timeout=86400)

    @classmethod
    def record_celery_failure(cls, task_name: str = 'unknown') -> None:
        """Incrementa el contador de fallos de tareas Celery."""
        try:
            cache.incr(f"{cls.METRICS_PREFIX}:celery_failures_total", 1)
        except Exception:
            cache.set(f"{cls.METRICS_PREFIX}:celery_failures_total", 1, timeout=86400)

    @classmethod
    def record_external_provider_call(cls, provider: str, success: bool = True, duration_ms: float = 0.0) -> None:
        """Registra una llamada a un proveedor externo (Google Books, OpenLibrary, etc.)."""
        try:
            cache.incr(f"{cls.METRICS_PREFIX}:external_calls:{provider}", 1)
        except Exception:
            cache.set(f"{cls.METRICS_PREFIX}:external_calls:{provider}", 1, timeout=86400)

        if not success:
            try:
                cache.incr(f"{cls.METRICS_PREFIX}:external_errors:{provider}", 1)
                cache.incr(f"{cls.METRICS_PREFIX}:external_errors_total", 1)
            except Exception:
                cache.set(f"{cls.METRICS_PREFIX}:external_errors_total", 1, timeout=86400)

    @classmethod
    def record_websocket_connection(cls, delta: int = 1) -> None:
        """Actualiza el indicador de conexiones activas por WebSocket."""
        try:
            count = cache.get(f"{cls.METRICS_PREFIX}:ws_connections") or 0
            new_count = max(0, int(count) + delta)
            cache.set(f"{cls.METRICS_PREFIX}:ws_connections", new_count, timeout=86400)
        except Exception:
            pass

    @classmethod
    def get_metrics(cls) -> Dict[str, Any]:
        """Calcula y devuelve el cuadro de mando de métricas operativas de la plataforma."""
        total_requests = int(cache.get(f"{cls.METRICS_PREFIX}:requests_total") or 0)
        requests_5xx = int(cache.get(f"{cls.METRICS_PREFIX}:requests_5xx") or 0)
        requests_4xx = int(cache.get(f"{cls.METRICS_PREFIX}:requests_4xx") or 0)
        celery_failures = int(cache.get(f"{cls.METRICS_PREFIX}:celery_failures_total") or 0)
        external_errors = int(cache.get(f"{cls.METRICS_PREFIX}:external_errors_total") or 0)
        ws_connections = int(cache.get(f"{cls.METRICS_PREFIX}:ws_connections") or 0)
        total_db_queries = int(cache.get(f"{cls.METRICS_PREFIX}:db_queries_total") or 0)

        samples = cache.get(f"{cls.METRICS_PREFIX}:latency_samples") or []
        if samples and isinstance(samples, list):
            sorted_samples = sorted(samples)
            latency_avg = round(sum(samples) / len(samples), 2)
            p95_idx = int(len(sorted_samples) * 0.95)
            latency_p95 = round(sorted_samples[min(p95_idx, len(sorted_samples) - 1)], 2)
        else:
            latency_avg = 0.0
            latency_p95 = 0.0

        rate_5xx_pct = round((requests_5xx / total_requests) * 100, 2) if total_requests > 0 else 0.0
        rate_4xx_pct = round((requests_4xx / total_requests) * 100, 2) if total_requests > 0 else 0.0
        db_queries_avg = round(total_db_queries / total_requests, 2) if total_requests > 0 else 0.0

        return {
            'requests': {
                'total': total_requests,
                'status_5xx_count': requests_5xx,
                'status_5xx_rate_pct': rate_5xx_pct,
                'status_4xx_count': requests_4xx,
                'status_4xx_rate_pct': rate_4xx_pct,
            },
            'latency_ms': {
                'average': latency_avg,
                'p95': latency_p95,
                'sample_size': len(samples) if isinstance(samples, list) else 0,
            },
            'database': {
                'total_queries': total_db_queries,
                'avg_queries_per_request': db_queries_avg,
            },
            'background_and_integrations': {
                'celery_failures_total': celery_failures,
                'external_api_errors_total': external_errors,
                'active_websocket_connections': ws_connections,
            },
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }


class StructuredLoggingMiddleware:
    """
    Middleware que asegura trazabilidad distribuida e intercepta cada petición HTTP:
    - Asigna o propaga request_id (X-Request-ID).
    - Cronometra la duración exacta del ciclo de petición en milisegundos.
    - Cuantifica las consultas ejecutadas contra la base de datos.
    - Registra el evento estructurado sin filtrar contraseñas o tokens.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Obtener o generar X-Request-ID
        request_id = (
            request.headers.get('X-Request-ID')
            or request.META.get('HTTP_X_REQUEST_ID')
            or str(uuid.uuid4())
        )
        request.request_id = request_id

        start_time = time.perf_counter()
        initial_queries = len(connection.queries) if connection else 0

        response = self.get_response(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        db_queries = (len(connection.queries) - initial_queries) if connection else 0
        user_id = getattr(getattr(request, 'user', None), 'id', None)

        # Inyectar X-Request-ID en los encabezados de respuesta
        response['X-Request-ID'] = request_id

        # Registrar métrica agregada
        ObservabilityMetricsService.record_request(
            status_code=response.status_code,
            duration_ms=duration_ms,
            db_queries=db_queries,
        )

        # Registrar log estructurado
        log_data = {
            'request_id': request_id,
            'user_id': user_id,
            'endpoint': request.path,
            'method': request.method,
            'status_code': response.status_code,
            'duration_ms': duration_ms,
            'db_queries': db_queries,
        }

        if response.status_code >= 500:
            logger.error("HTTP Request Failed: %s %s %s", request.method, request.path, response.status_code, extra=log_data)
        elif response.status_code >= 400:
            logger.warning("HTTP Request Client Warning: %s %s %s", request.method, request.path, response.status_code, extra=log_data)
        else:
            logger.info("HTTP Request Completed: %s %s %s", request.method, request.path, response.status_code, extra=log_data)

        return response

    def process_exception(self, request, exception):
        """Registra información estructurada de cualquier excepción no capturada."""
        request_id = getattr(request, 'request_id', 'unknown')
        user_id = getattr(getattr(request, 'user', None), 'id', None)
        logger.error(
            "Unhandled Exception during request %s: %s",
            request_id,
            str(exception),
            extra={
                'request_id': request_id,
                'user_id': user_id,
                'endpoint': getattr(request, 'path', 'unknown'),
                'method': getattr(request, 'method', 'unknown'),
                'status_code': 500,
                'error': str(exception),
                'exception': f"{type(exception).__name__}: {str(exception)}",
            },
            exc_info=True
        )
        return None


class ObservabilityMetricsView(APIView):
    """
    Endpoint administrativo que expone las métricas consolidadas del sistema.
    Solo accesible para usuarios administradores o moderadores autorizados.
    """
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        summary="Métricas de observabilidad del sistema",
        description="Devuelve métricas consolidadas de latencia (promedio y p95), ratios de errores 5xx/4xx, consultas SQL y proveedores externos.",
        responses={
            200: OpenApiResponse(description="Cuadro de mando de métricas operativas"),
            401: OpenApiResponse(description="No autenticado"),
            403: OpenApiResponse(description="Permiso denegado (requiere administrador)"),
        },
        tags=['Observability'],
    )
    def get(self, request):
        metrics = ObservabilityMetricsService.get_metrics()
        return Response(metrics, status=status.HTTP_200_OK)

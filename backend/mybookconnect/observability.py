"""
Módulo de Observabilidad, Telemetría y Alertas de Producción.
Fase 14 — Observabilidad (RoadmapV2, Sección 19).

Proporciona:
- StructuredLoggingMiddleware: Middleware HTTP para inyección de request_id,
  medición de latencia, conteo de consultas SQL y logging estructurado en JSON.
- ObservabilityMetricsService: Agregador de métricas operativas de backend
  (latencia percentiles p50/p95/p99, 4xx/5xx, DB latency, Redis latency, Celery backlog, WS).
- ProductMetricsService: Agregador de métricas de producto y engagement
  (DAU, WAU, MAU, retención, libros agregados, reseñas, seguimiento social, mensajes, recs).
- SystemAlertsEvaluator: Motor de evaluación de alertas de salud operativa
  (5xx elevado, DB/Redis unavailable, Celery backlog, saturación de disco/memoria, tasa de error).
- ObservabilityMetricsView: Endpoint administrativo seguro (/api/v1/observability/metrics/).
"""
import datetime
import logging
import os
import shutil
import time
import uuid
from typing import Any, Dict

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mybookconnect.logging_formatters import StructuredJsonFormatter, sanitize_sensitive_data

__all__ = [
    'ObservabilityMetricsService',
    'ProductMetricsService',
    'SystemAlertsEvaluator',
    'ObservabilityMetricsView',
    'StructuredLoggingMiddleware',
    'StructuredJsonFormatter',
    'sanitize_sensitive_data',
]

logger = logging.getLogger('mybookconnect.structured')


class ObservabilityMetricsService:
    """
    Servicio de agregación y cálculo de métricas operativas y de rendimiento de backend.
    Fase 14 — Sección 19.2 (Backend: requests, latency, 5xx, 4xx, DB latency, Redis latency,
    Celery queue, Celery failures, WebSocket connections).
    """
    METRICS_PREFIX = 'mbc:metrics'
    MAX_LATENCY_SAMPLES = 200

    @classmethod
    def record_request(
        cls,
        status_code: int,
        duration_ms: float,
        db_queries: int = 0,
        db_duration_ms: float = 0.0,
    ) -> None:
        """Registra una petición HTTP procesada con su código, duración y consultas SQL."""
        try:
            cache.incr(f"{cls.METRICS_PREFIX}:requests_total", 1)
        except Exception:
            try:
                cache.set(f"{cls.METRICS_PREFIX}:requests_total", 1, timeout=86400)
            except Exception:
                pass

        if status_code >= 500:
            try:
                cache.incr(f"{cls.METRICS_PREFIX}:requests_5xx", 1)
            except Exception:
                try:
                    cache.set(f"{cls.METRICS_PREFIX}:requests_5xx", 1, timeout=86400)
                except Exception:
                    pass
        elif status_code >= 400:
            try:
                cache.incr(f"{cls.METRICS_PREFIX}:requests_4xx", 1)
            except Exception:
                try:
                    cache.set(f"{cls.METRICS_PREFIX}:requests_4xx", 1, timeout=86400)
                except Exception:
                    pass

        # Muestreo circular de latencias generales en caché
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
            try:
                cache.set(f"{cls.METRICS_PREFIX}:db_queries_total", db_queries, timeout=86400)
            except Exception:
                pass

        # Muestreo de latencia de DB si fue registrada
        if db_duration_ms > 0:
            try:
                db_samples_key = f"{cls.METRICS_PREFIX}:db_latency_samples"
                db_samples = cache.get(db_samples_key) or []
                if not isinstance(db_samples, list):
                    db_samples = []
                db_samples.append(db_duration_ms)
                if len(db_samples) > cls.MAX_LATENCY_SAMPLES:
                    db_samples = db_samples[-cls.MAX_LATENCY_SAMPLES:]
                cache.set(db_samples_key, db_samples, timeout=3600)
            except Exception:
                pass

    @classmethod
    def record_celery_failure(cls, task_name: str = 'unknown') -> None:
        """Incrementa el contador acumulativo de fallos en tareas Celery."""
        try:
            cache.incr(f"{cls.METRICS_PREFIX}:celery_failures_total", 1)
        except Exception:
            cache.set(f"{cls.METRICS_PREFIX}:celery_failures_total", 1, timeout=86400)

    @classmethod
    def record_external_provider_call(cls, provider: str, success: bool = True, duration_ms: float = 0.0) -> None:
        """Registra una llamada a un proveedor externo (Google Books, OpenLibrary, IA, etc.)."""
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
    def measure_redis_latency(cls) -> float:
        """Mide la latencia de ida y vuelta (round-trip) en milisegundos contra Redis."""
        t_start = time.perf_counter()
        try:
            cache.set("mbc:latency_ping", "1", timeout=5)
            cache.get("mbc:latency_ping")
            return round((time.perf_counter() - t_start) * 1000, 2)
        except Exception:
            return -1.0

    @classmethod
    def measure_db_latency(cls) -> float:
        """Mide la latencia de una consulta SELECT 1 en milisegundos contra PostgreSQL."""
        t_start = time.perf_counter()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            return round((time.perf_counter() - t_start) * 1000, 2)
        except Exception:
            return -1.0

    @classmethod
    def get_celery_queue_depth(cls) -> int:
        """Obtiene la profundidad actual de la cola de tareas Celery inspeccionando Redis."""
        try:
            # Si el cliente redis nativo está disponible a través de cache
            raw_client = getattr(cache, '_cache', None) or getattr(cache, 'client', None)
            if hasattr(raw_client, 'get_client'):
                client = raw_client.get_client()
                return int(client.llen("celery"))
            elif hasattr(raw_client, 'llen'):
                return int(raw_client.llen("celery"))
        except Exception:
            pass
        return 0

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

        # Muestreo general de latencia
        samples = cache.get(f"{cls.METRICS_PREFIX}:latency_samples") or []
        if samples and isinstance(samples, list):
            sorted_samples = sorted(samples)
            latency_avg = round(sum(samples) / len(samples), 2)
            p50_idx = int(len(sorted_samples) * 0.50)
            p95_idx = int(len(sorted_samples) * 0.95)
            p99_idx = int(len(sorted_samples) * 0.99)
            latency_p50 = round(sorted_samples[min(p50_idx, len(sorted_samples) - 1)], 2)
            latency_p95 = round(sorted_samples[min(p95_idx, len(sorted_samples) - 1)], 2)
            latency_p99 = round(sorted_samples[min(p99_idx, len(sorted_samples) - 1)], 2)
        else:
            latency_avg = 0.0
            latency_p50 = 0.0
            latency_p95 = 0.0
            latency_p99 = 0.0

        # Latencias activas de dependencias
        db_latency_ms = cls.measure_db_latency()
        redis_latency_ms = cls.measure_redis_latency()
        celery_queue_depth = cls.get_celery_queue_depth()

        rate_5xx_pct = round((requests_5xx / total_requests) * 100, 2) if total_requests > 0 else 0.0
        rate_4xx_pct = round((requests_4xx / total_requests) * 100, 2) if total_requests > 0 else 0.0
        db_queries_avg = round(total_db_queries / total_requests, 2) if total_requests > 0 else 0.0

        p95_budget_ms = 500.0
        p99_budget_ms = 1500.0
        critical_queries_budget_ms = 100.0
        budgets_healthy = (latency_p95 <= p95_budget_ms) and (latency_p99 <= p99_budget_ms)

        backend_data = {
            'requests': {
                'total': total_requests,
                'status_5xx_count': requests_5xx,
                'status_5xx_rate_pct': rate_5xx_pct,
                'status_4xx_count': requests_4xx,
                'status_4xx_rate_pct': rate_4xx_pct,
            },
            'latency_ms': {
                'average': latency_avg,
                'p50': latency_p50,
                'p95': latency_p95,
                'p99': latency_p99,
                'sample_size': len(samples) if isinstance(samples, list) else 0,
            },
            'database': {
                'total_queries': total_db_queries,
                'avg_queries_per_request': db_queries_avg,
                'latency_ms': db_latency_ms,
                'status': 'healthy' if db_latency_ms >= 0 else 'unhealthy',
            },
            'redis': {
                'latency_ms': redis_latency_ms,
                'status': 'healthy' if redis_latency_ms >= 0 else 'unhealthy',
            },
            'background_and_integrations': {
                'celery_failures_total': celery_failures,
                'celery_queue_depth': celery_queue_depth,
                'external_api_errors_total': external_errors,
                'active_websocket_connections': ws_connections,
            },
            'performance_budgets': {
                'api_p95_budget_ms': p95_budget_ms,
                'api_p99_budget_ms': p99_budget_ms,
                'critical_queries_budget_ms': critical_queries_budget_ms,
                'is_within_budget': budgets_healthy,
                'status': 'within_budget' if budgets_healthy else 'breached',
            },
        }

        # Preservar estructura compatible con contratos de API previos en el nivel raíz
        response_dict = dict(backend_data)
        response_dict['backend_metrics'] = backend_data
        response_dict['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        return response_dict


class ProductMetricsService:
    """
    Servicio de cálculo y consolidación de métricas de producto y engagement.
    Fase 14 — Sección 19.2 (Producto: DAU, WAU, MAU, retention, books added,
    reviews, follows, messages, recommendation interactions).
    """
    CACHE_KEY = 'mbc:metrics:product'
    CACHE_TTL_SECONDS = 60  # 1 minuto de caché para optimizar consultas de base de datos

    @classmethod
    def get_product_metrics(cls) -> Dict[str, Any]:
        """Calcula las métricas de producto y actividad social de la plataforma."""
        cached = cache.get(cls.CACHE_KEY)
        if cached is not None and isinstance(cached, dict):
            return cached

        User = get_user_model()
        now = timezone.now()

        # 1. Usuarios activos en periodos temporales (DAU, WAU, MAU)
        dau_threshold = now - datetime.timedelta(days=1)
        wau_threshold = now - datetime.timedelta(days=7)
        mau_threshold = now - datetime.timedelta(days=30)

        total_users = User.objects.count()
        dau = User.objects.filter(last_login__gte=dau_threshold).count()
        wau = User.objects.filter(last_login__gte=wau_threshold).count()
        mau = User.objects.filter(last_login__gte=mau_threshold).count()

        # Ratio de retención (WAU / MAU)
        retention_rate_pct = round((wau / mau) * 100, 2) if mau > 0 else (100.0 if total_users > 0 else 0.0)

        # 2. Libros agregados a estanterías
        books_added = 0
        try:
            from books.models import UserBook
            books_added = UserBook.objects.count()
        except Exception:
            pass

        # 3. Reseñas creadas activas (no eliminadas)
        reviews_count = 0
        try:
            from books.models import Review
            reviews_count = Review.objects.filter(deleted_at__isnull=True).count()
        except Exception:
            pass

        # 4. Conexiones sociales (Follows)
        follows_count = 0
        try:
            follows_count = User.following.through.objects.count()
        except Exception:
            pass

        # 5. Mensajes intercambiados en el sistema de chat
        messages_count = 0
        try:
            from messages_app.models import Message
            messages_count = Message.objects.count()
        except Exception:
            pass

        # 6. Interacciones con el motor de recomendaciones
        rec_interactions_count = 0
        try:
            from books.models import RecommendationFeedback
            rec_interactions_count = RecommendationFeedback.objects.count()
        except Exception:
            pass

        product_metrics = {
            'dau': dau,
            'wau': wau,
            'mau': mau,
            'total_users': total_users,
            'retention_rate_pct': retention_rate_pct,
            'books_added': books_added,
            'reviews': reviews_count,
            'follows': follows_count,
            'messages': messages_count,
            'recommendation_interactions': rec_interactions_count,
            'calculated_at': now.isoformat(),
        }

        try:
            cache.set(cls.CACHE_KEY, product_metrics, timeout=cls.CACHE_TTL_SECONDS)
        except Exception:
            pass

        return product_metrics


class SystemAlertsEvaluator:
    """
    Motor de evaluación en tiempo real de umbrales y alertas operativas.
    Fase 14 — Sección 19.3 (Alertas: 5xx elevado, DB unavailable, Redis unavailable,
    Celery backlog, disk usage, memory, error rate).
    """
    @classmethod
    def evaluate_alerts(
        cls,
        backend_metrics: Dict[str, Any],
        product_metrics: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Evalúa los 7 criterios de alerta y genera el estado consolidado de la plataforma."""
        alerts = []
        overall_status = "HEALTHY"

        requests_info = backend_metrics.get('requests', {})
        total_requests = requests_info.get('total', 0)
        rate_5xx = requests_info.get('status_5xx_rate_pct', 0.0)
        rate_4xx = requests_info.get('status_4xx_rate_pct', 0.0)
        db_info = backend_metrics.get('database', {})
        redis_info = backend_metrics.get('redis', {})
        bg_info = backend_metrics.get('background_and_integrations', {})
        celery_queue = bg_info.get('celery_queue_depth', 0)

        # 1. Alerta: 5xx elevado (> 1% con muestra mínima de peticiones)
        if rate_5xx > 1.0 and total_requests >= 10:
            alerts.append({
                'id': 'high_5xx_rate',
                'severity': 'CRITICAL',
                'message': f"Tasa de errores 5xx elevada: {rate_5xx}% (umbral: 1.0%)",
            })
            overall_status = "CRITICAL"

        # 2. Alerta: Base de datos no disponible
        if db_info.get('status') != 'healthy':
            alerts.append({
                'id': 'db_unavailable',
                'severity': 'CRITICAL',
                'message': "La base de datos relacional PostgreSQL no responde a peticiones.",
            })
            overall_status = "CRITICAL"

        # 3. Alerta: Redis no disponible
        if redis_info.get('status') != 'healthy':
            alerts.append({
                'id': 'redis_unavailable',
                'severity': 'CRITICAL',
                'message': "El servidor de caché y mensajería Redis no responde a ping.",
            })
            overall_status = "CRITICAL"

        # 4. Alerta: Celery backlog (> 100 tareas acumuladas)
        if celery_queue > 100:
            alerts.append({
                'id': 'celery_backlog',
                'severity': 'WARNING',
                'message': f"Cola de Celery saturada con {celery_queue} tareas pendientes (umbral: 100)",
            })
            if overall_status != "CRITICAL":
                overall_status = "DEGRADED"

        # 5. Alerta: Uso de disco (> 85% de capacidad)
        disk_pct = 0.0
        try:
            total_disk, used_disk, free_disk = shutil.disk_usage(os.getcwd())
            disk_pct = round((used_disk / total_disk) * 100, 1)
            if disk_pct > 85.0:
                alerts.append({
                    'id': 'disk_usage_high',
                    'severity': 'WARNING',
                    'message': f"Uso de almacenamiento en disco elevado: {disk_pct}% (umbral: 85.0%)",
                })
                if overall_status != "CRITICAL":
                    overall_status = "DEGRADED"
        except Exception:
            pass

        # 6. Alerta: Uso de memoria
        memory_pct = 0.0
        try:
            import psutil
            memory_pct = psutil.virtual_memory().percent
            if memory_pct > 85.0:
                alerts.append({
                    'id': 'memory_usage_high',
                    'severity': 'WARNING',
                    'message': f"Uso de memoria RAM elevado: {memory_pct}% (umbral: 85.0%)",
                })
                if overall_status != "CRITICAL":
                    overall_status = "DEGRADED"
        except Exception:
            # Fallback en caso de que psutil no esté disponible
            pass

        # 7. Alerta: Error rate global combinado (> 5% de 4xx+5xx)
        combined_error_rate = round(rate_5xx + rate_4xx, 2)
        if combined_error_rate > 5.0 and total_requests >= 20:
            alerts.append({
                'id': 'high_error_rate',
                'severity': 'WARNING',
                'message': f"Tasa de error HTTP combinada anormal: {combined_error_rate}% (umbral: 5.0%)",
            })
            if overall_status != "CRITICAL":
                overall_status = "DEGRADED"

        return {
            'overall_status': overall_status,
            'active_alerts_count': len(alerts),
            'alerts': alerts,
            'system_metrics': {
                'disk_usage_pct': disk_pct,
                'memory_usage_pct': memory_pct,
            },
        }


class StructuredLoggingMiddleware:
    """
    Middleware que asegura trazabilidad distribuida e intercepta cada petición HTTP:
    - Asigna o propaga request_id (X-Request-ID).
    - Cronometra la duración exacta del ciclo de petición en milisegundos.
    - Cuantifica las consultas ejecutadas contra la base de datos.
    - Registra el evento estructurado con los 7 campos obligatorios de la Fase 14.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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

        response['X-Request-ID'] = request_id

        # Registrar métrica agregada
        ObservabilityMetricsService.record_request(
            status_code=response.status_code,
            duration_ms=duration_ms,
            db_queries=db_queries,
        )

        # Campos estructurados obligatorios (Fase 14 - Sección 19.1)
        log_data = {
            'request_id': request_id,
            'user_id': user_id,
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration': duration_ms,
            # Campos complementarios
            'endpoint': request.path,
            'status_code': response.status_code,
            'duration_ms': duration_ms,
            'db_queries': db_queries,
        }

        if response.status_code >= 500:
            logger.error(
                "HTTP Request Failed: %s %s %s",
                request.method,
                request.path,
                response.status_code,
                extra=log_data,
            )
        elif response.status_code >= 400:
            logger.warning(
                "HTTP Request Client Warning: %s %s %s",
                request.method,
                request.path,
                response.status_code,
                extra=log_data,
            )
        else:
            logger.info(
                "HTTP Request Completed: %s %s %s",
                request.method,
                request.path,
                response.status_code,
                extra=log_data,
            )

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
                'method': getattr(request, 'method', 'unknown'),
                'path': getattr(request, 'path', 'unknown'),
                'status': 500,
                'duration': 0.0,
                'endpoint': getattr(request, 'path', 'unknown'),
                'status_code': 500,
                'error': str(exception),
                'exception': f"{type(exception).__name__}: {str(exception)}",
            },
            exc_info=True,
        )
        return None


class ObservabilityMetricsView(APIView):
    """
    Endpoint administrativo consolidado para observabilidad, métricas y alertas.
    Fase 14 — Secciones 19.2 y 19.3.
    Solo accesible para administradores o personal autorizado.
    """
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        summary="Métricas y alertas de observabilidad del sistema",
        description="Devuelve el cuadro de mando integral con métricas de backend (latencias, queries, Celery, WS), métricas de producto (DAU, WAU, MAU, retención) y evaluación de alertas de salud operativa.",
        responses={
            200: OpenApiResponse(description="Cuadro de mando consolidado de observabilidad"),
            401: OpenApiResponse(description="No autenticado"),
            403: OpenApiResponse(description="Permiso denegado (requiere permisos de administrador)"),
        },
        tags=['Observability'],
    )
    def get(self, request):
        backend_metrics = ObservabilityMetricsService.get_metrics()
        product_metrics = ProductMetricsService.get_product_metrics()
        alerts_eval = SystemAlertsEvaluator.evaluate_alerts(backend_metrics, product_metrics)

        # Respuesta integral consolidada
        response_payload = dict(backend_metrics)
        response_payload['backend_metrics'] = backend_metrics.get('backend_metrics', {})
        response_payload['product_metrics'] = product_metrics
        response_payload['system_alerts'] = alerts_eval
        response_payload['timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return Response(response_payload, status=status.HTTP_200_OK)

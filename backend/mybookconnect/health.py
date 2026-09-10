import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Endpoint de comprobación de salud para orquestadores (Docker, Kubernetes, reverse proxy).
    Verifica conectividad en tiempo real con PostgreSQL y Redis.
    No depende de servicios externos de IA.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    @extend_schema(
        summary="Health check del sistema",
        description="Comprueba el estado operativo de Django, PostgreSQL y Redis.",
        responses={
            200: OpenApiResponse(description="Todos los servicios operativos."),
            503: OpenApiResponse(description="Uno o más servicios degradados."),
        },
    )
    def get(self, request):
        services = {}
        all_healthy = True

        # 1. Comprobación de PostgreSQL
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            services["database"] = "healthy"
        except Exception as exc:
            logger.error("Health check fallo en base de datos: %s", exc)
            services["database"] = f"unhealthy: {exc}"
            all_healthy = False

        # 2. Comprobación de Redis (Caché)
        try:
            cache.set("healthcheck_ping", "ok", timeout=10)
            val = cache.get("healthcheck_ping")
            if val == "ok":
                services["cache"] = "healthy"
            else:
                services["cache"] = "unhealthy: cache value mismatch"
                all_healthy = False
        except Exception as exc:
            logger.error("Health check fallo en cache: %s", exc)
            services["cache"] = f"unhealthy: {exc}"
            all_healthy = False

        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": "healthy" if all_healthy else "unhealthy",
                "services": services,
            },
            status=status_code,
        )

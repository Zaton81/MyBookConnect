import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .version import get_version, get_version_info

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """
    Sonda de Liveness (proceso activo).
    Verifica que el proceso Django/Daphne esté levantado y responda a peticiones HTTP.
    No depende de servicios externos para evitar reinicios innecesarios del contenedor.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    @extend_schema(
        summary="Liveness check del proceso",
        description="Comprueba que el proceso de la aplicación Django está vivo y responde HTTP.",
        responses={
            200: OpenApiResponse(description="Proceso web operativo."),
        },
    )
    def get(self, request):
        return Response(
            {
                "status": "healthy",
                "process": "alive",
                "version": get_version(),
            },
            status=status.HTTP_200_OK,
        )


class VersionView(APIView):
    """
    Endpoint informativo con la versión actual de la API y metadatos SemVer.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    @extend_schema(
        summary="Información de versión de la API",
        description="Devuelve la versión SemVer actual de MyBookConnect y metadatos de versión.",
        responses={
            200: OpenApiResponse(description="Metadatos de versión obtenidos con éxito."),
        },
    )
    def get(self, request):
        return Response(get_version_info(), status=status.HTTP_200_OK)


class ReadinessCheckView(APIView):
    """
    Sonda de Readiness (preparado para recibir tráfico).
    Verifica que las dependencias críticas (PostgreSQL y Redis) estén operativas
    antes de dirigir tráfico de usuarios a este contenedor.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    @extend_schema(
        summary="Readiness check del sistema",
        description="Comprueba la conectividad con PostgreSQL y Redis para aceptar tráfico.",
        responses={
            200: OpenApiResponse(description="Todos los servicios operativos para recibir tráfico."),
            503: OpenApiResponse(description="Uno o más servicios dependientes no disponibles."),
        },
    )
    def get(self, request):
        services = {}
        all_ready = True

        # 1. Comprobación de PostgreSQL (Database)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
            services["database"] = "ready"
        except Exception as exc:
            logger.error("Readiness check fallo en base de datos: %s", exc)
            services["database"] = f"unhealthy: {exc}"
            all_ready = False

        # 2. Comprobación de Redis (Caché)
        try:
            cache.set("readiness_ping", "ok", timeout=10)
            val = cache.get("readiness_ping")
            if val == "ok":
                services["cache"] = "ready"
            else:
                services["cache"] = "unhealthy: cache value mismatch"
                all_ready = False
        except Exception as exc:
            logger.error("Readiness check fallo en cache: %s", exc)
            services["cache"] = f"unhealthy: {exc}"
            all_ready = False

        status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(
            {
                "status": "ready" if all_ready else "not_ready",
                "services": services,
            },
            status=status_code,
        )

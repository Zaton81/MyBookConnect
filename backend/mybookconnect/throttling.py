"""
Throttling resiliente ante caídas de caché / Redis.
Permite la degradación elegante de la API (Requisito 13.5 de RoadmapV2) sin responder 500
cuando el backend de caché temporalmente no responde o falla la conexión a Redis.
"""
import logging

from rest_framework.throttling import AnonRateThrottle, SimpleRateThrottle, UserRateThrottle

logger = logging.getLogger(__name__)


class ResilientThrottleMixin:
    """
    Mixin que envuelve las operaciones de caché de DRF throttling
    en bloques defensivos para degradar elegantemente ante cortes de Redis.
    """

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception as exc:
            logger.warning("Fallo en backend de throttling (Caché/Redis no disponible): %s. Permitiendo petición en modo degradado.", exc)
            return True

    def throttle_success(self):
        try:
            return super().throttle_success()
        except Exception as exc:
            logger.warning("Fallo al actualizar clave de throttling en caché: %s.", exc)
            return True


class ResilientAnonRateThrottle(ResilientThrottleMixin, AnonRateThrottle):
    pass


class ResilientUserRateThrottle(ResilientThrottleMixin, UserRateThrottle):
    pass


class ResilientSimpleRateThrottle(ResilientThrottleMixin, SimpleRateThrottle):
    pass

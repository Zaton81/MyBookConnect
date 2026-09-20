"""
Módulo de Idempotencia para MyBookConnect (Fase 62).

Proporciona soporte estándar para la cabecera `Idempotency-Key` (IETF HTTP draft),
permitiendo la ejecución segura de operaciones sensibles o costosas con tolerancia
a reintentos de red automáticos.

Características:
- Detección de claves vía `Idempotency-Key` o `X-Idempotency-Key`.
- Control de concurrencia y carreras mediante bloqueos atómicos en Redis (retorno 409 Conflict).
- Verificación de discrepancia de payload (mismo key con distinto cuerpo -> 400 Bad Request).
- Retransmisión transparente de respuestas en caché con cabecera `Idempotent-Replayed: true`.
- Decorador `@idempotent` para vistas DRF y utilidades para middleware.
"""

import functools
import hashlib
import json
import logging
from typing import Any, Callable, Dict, Optional

from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger("mybookconnect.idempotency")

DEFAULT_IDEMPOTENCY_TIMEOUT = 86400  # 24 horas
IN_PROGRESS_LOCK_TIMEOUT = 60  # 60 segundos para operaciones en curso
MAX_KEY_LENGTH = 128


class IdempotencyStatus:
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class IdempotencyManager:
    """
    Gestiona el ciclo de vida de peticiones idempotentes en caché Redis.
    """

    CACHE_PREFIX = "idemp"

    @classmethod
    def extract_key(cls, request) -> Optional[str]:
        """
        Extrae y valida la clave de idempotencia desde las cabeceras HTTP.
        Soporta 'Idempotency-Key' y 'X-Idempotency-Key'.
        """
        key = request.META.get("HTTP_IDEMPOTENCY_KEY") or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
        if not key:
            return None
        key = str(key).strip()
        if not key or len(key) > MAX_KEY_LENGTH:
            return None
        return key

    @classmethod
    def compute_payload_hash(cls, request) -> str:
        """
        Calcula un hash SHA-256 determinista del cuerpo y parámetros de la petición.
        """
        hasher = hashlib.sha256()

        raw_data = getattr(request, "data", None)
        if raw_data is None:
            body = getattr(request, "body", b"")
            if body:
                try:
                    raw_data = json.loads(body.decode("utf-8"))
                except Exception:
                    raw_data = body

        if raw_data is not None:
            if isinstance(raw_data, (dict, list)):
                try:
                    encoded = json.dumps(raw_data, sort_keys=True, default=str).encode("utf-8")
                    hasher.update(encoded)
                except Exception:
                    hasher.update(str(raw_data).encode("utf-8"))
            elif isinstance(raw_data, bytes):
                hasher.update(raw_data)
            else:
                hasher.update(str(raw_data).encode("utf-8"))

        # Incluir query parameters
        query_params = getattr(request, "GET", None)
        if query_params:
            sorted_params = sorted(query_params.lists())
            hasher.update(str(sorted_params).encode("utf-8"))

        return hasher.hexdigest()

    @classmethod
    def build_cache_key(cls, user_id: Any, method: str, path: str, key: str) -> str:
        """
        Construye la clave de almacenamiento en Redis con espacio de nombres seguro.
        """
        user_identifier = str(user_id) if user_id and str(user_id) != "None" else "anon"
        normalized_path = path.strip("/")
        return f"{cls.CACHE_PREFIX}:{user_identifier}:{method.upper()}:{normalized_path}:{key}"

    @classmethod
    def build_lock_key(cls, cache_key: str) -> str:
        return f"lock:{cache_key}"

    @classmethod
    def acquire_lock(cls, cache_key: str, timeout: int = IN_PROGRESS_LOCK_TIMEOUT) -> bool:
        """
        Adquiere un bloqueo atómico en Redis para prevenir peticiones simultáneas idénticas.
        """
        lock_key = cls.build_lock_key(cache_key)
        # cache.add retorna True solo si la clave no existía previamente
        return bool(cache.add(lock_key, "1", timeout=timeout))

    @classmethod
    def release_lock(cls, cache_key: str) -> None:
        """
        Libera el bloqueo atómico.
        """
        lock_key = cls.build_lock_key(cache_key)
        try:
            cache.delete(lock_key)
        except Exception as e:
            logger.debug("Error liberando bloqueo de idempotencia: %s", e)

    @classmethod
    def get_stored_record(cls, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Recupera el registro de idempotencia guardado en Redis.
        """
        try:
            return cache.get(cache_key)
        except Exception as e:
            logger.warning("Error leyendo registro de idempotencia en Redis: %s", e)
            return None

    @classmethod
    def set_processing(
        cls,
        cache_key: str,
        payload_hash: str,
        timeout: int = IN_PROGRESS_LOCK_TIMEOUT,
    ) -> None:
        """
        Marca la solicitud como en proceso en la caché.
        """
        record = {
            "status": IdempotencyStatus.PROCESSING,
            "payload_hash": payload_hash,
        }
        try:
            cache.set(cache_key, record, timeout=timeout)
        except Exception as e:
            logger.warning("Error guardando estado PROCESSING de idempotencia: %s", e)

    @classmethod
    def save_response(
        cls,
        cache_key: str,
        payload_hash: str,
        status_code: int,
        response_data: Any,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = DEFAULT_IDEMPOTENCY_TIMEOUT,
    ) -> None:
        """
        Almacena la respuesta completada en Redis para futuras retransmisiones.
        """
        record = {
            "status": IdempotencyStatus.COMPLETED,
            "payload_hash": payload_hash,
            "status_code": status_code,
            "response_data": response_data,
            "headers": headers or {},
        }
        try:
            cache.set(cache_key, record, timeout=timeout)
        except Exception as e:
            logger.warning("Error guardando respuesta de idempotencia: %s", e)


def idempotent(
    required: bool = False,
    timeout: int = DEFAULT_IDEMPOTENCY_TIMEOUT,
) -> Callable:
    """
    Decorador para métodos de vistas DRF (post, put, patch) que implementa
    la semántica de idempotencia basada en la cabecera Idempotency-Key.

    Uso:
        class ImportBookView(APIView):
            @idempotent(required=False, timeout=86400)
            def post(self, request):
                ...
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(self_or_view, request, *args, **kwargs):
            # Marcar la petición para evitar reprocesamiento en el middleware
            request._idempotency_handled = True

            idempotency_key = IdempotencyManager.extract_key(request)

            # Si la clave no está presente y no es requerida, ejecutar normalmente
            if not idempotency_key:
                if required:
                    return Response(
                        {
                            "detail": "Se requiere la cabecera Idempotency-Key para esta operación.",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Se requiere la cabecera Idempotency-Key para esta operación.",
                                "details": {"header": "Idempotency-Key missing"},
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                return view_func(self_or_view, request, *args, **kwargs)

            # Validar longitud
            raw_key_header = request.META.get("HTTP_IDEMPOTENCY_KEY") or request.META.get("HTTP_X_IDEMPOTENCY_KEY")
            if raw_key_header and len(str(raw_key_header).strip()) > MAX_KEY_LENGTH:
                return Response(
                    {
                        "detail": f"La clave de idempotencia excede el máximo permitido ({MAX_KEY_LENGTH} caracteres).",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": f"La clave de idempotencia excede el máximo permitido ({MAX_KEY_LENGTH} caracteres).",
                            "details": {"idempotency_key": "Too long"},
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_id = getattr(request.user, "id", None) if getattr(request, "user", None) and request.user.is_authenticated else None
            cache_key = IdempotencyManager.build_cache_key(
                user_id=user_id,
                method=request.method,
                path=request.path,
                key=idempotency_key,
            )
            payload_hash = IdempotencyManager.compute_payload_hash(request)

            # 1. Comprobar si ya existe un registro previo
            stored = IdempotencyManager.get_stored_record(cache_key)

            if stored:
                # Comprobar si el payload coincide
                if stored.get("payload_hash") != payload_hash:
                    return Response(
                        {
                            "detail": "La clave de idempotencia ya fue utilizada con un cuerpo de petición diferente.",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "La clave de idempotencia ya fue utilizada con un cuerpo de petición diferente.",
                                "details": {"idempotency_key": "Payload mismatch for reused key"},
                            },
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Si aún está en proceso -> 409 Conflict
                if stored.get("status") == IdempotencyStatus.PROCESSING:
                    return Response(
                        {
                            "detail": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                            "error": {
                                "code": "VALIDATION_ERROR",
                                "message": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                                "details": {"idempotency_key": "Request in progress"},
                            },
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                # Si ya fue completada exitosamente -> Retransmitir respuesta almacenada
                if stored.get("status") == IdempotencyStatus.COMPLETED:
                    cached_status = stored.get("status_code", 200)
                    cached_data = stored.get("response_data")
                    resp = Response(cached_data, status=cached_status)
                    resp["Idempotent-Replayed"] = "true"
                    resp["Idempotency-Key"] = idempotency_key
                    return resp

            # 2. Intentar adquirir bloqueo atómico para evitar carreras
            lock_acquired = IdempotencyManager.acquire_lock(cache_key)
            if not lock_acquired:
                return Response(
                    {
                        "detail": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Existe una solicitud idéntica en proceso con esta clave de idempotencia.",
                            "details": {"idempotency_key": "Concurrent request lock active"},
                        },
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            # Marcar estado PROCESSING
            IdempotencyManager.set_processing(cache_key, payload_hash)

            try:
                # Ejecutar la vista original
                response = view_func(self_or_view, request, *args, **kwargs)

                # Guardar en caché respuestas exitosas o deterministas (2xx, 4xx controlados)
                # No cachear errores 5xx (transitorios) para permitir reintento real
                if hasattr(response, "status_code") and response.status_code < 500:
                    resp_data = getattr(response, "data", None)
                    IdempotencyManager.save_response(
                        cache_key=cache_key,
                        payload_hash=payload_hash,
                        status_code=response.status_code,
                        response_data=resp_data,
                        timeout=timeout,
                    )

                if hasattr(response, "__setitem__"):
                    response["Idempotency-Key"] = idempotency_key

                return response

            finally:
                # Siempre liberar el bloqueo atómico
                IdempotencyManager.release_lock(cache_key)

        return wrapper

    return decorator

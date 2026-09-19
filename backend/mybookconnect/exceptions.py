"""
Manejador centralizado de excepciones y contrato unificado de errores API (Fase 61).

Implementa el estándar de respuesta ante errores:
{
  "error": {
    "code": "CODIGO_ESTABLE",
    "message": "Mensaje legible para humanos.",
    "details": { ... }
  }
}

Códigos de error estables requeridos por el Roadmap:
- AUTH_INVALID
- PERMISSION_DENIED
- NOT_FOUND
- VALIDATION_ERROR
- REVIEW_ALREADY_EXISTS
- BOOK_DUPLICATE
- USER_BLOCKED
- RATE_LIMITED
"""

import logging
from typing import Any, Dict

from rest_framework import exceptions, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class ErrorCode:
    AUTH_INVALID = "AUTH_INVALID"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    REVIEW_ALREADY_EXISTS = "REVIEW_ALREADY_EXISTS"
    BOOK_DUPLICATE = "BOOK_DUPLICATE"
    USER_BLOCKED = "USER_BLOCKED"
    RATE_LIMITED = "RATE_LIMITED"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"


# ─── Excepciones Específicas de Dominio ───


class ReviewAlreadyExistsError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El usuario ya tiene una reseña para este libro."
    default_code = ErrorCode.REVIEW_ALREADY_EXISTS


class BookDuplicateError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Ya existe un libro registrado con este ISBN o título/autor."
    default_code = ErrorCode.BOOK_DUPLICATE


class UserBlockedError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Acción bloqueada debido a una restricción de privacidad, silenciamiento o bloqueo activo entre usuarios."
    default_code = ErrorCode.USER_BLOCKED


class RateLimitedError(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Límite de peticiones excedido. Por favor, inténtelo de nuevo más tarde."
    default_code = ErrorCode.RATE_LIMITED


def normalize_error_data(
    orig_data: Any, status_code: int, exc: Exception | None = None, method: str = ""
) -> Dict[str, Any]:
    """
    Normaliza cualquier payload de error para ajustarse al contrato unificado:
    {"error": {"code": "...", "message": "...", "details": {...}}}
    preservando retrocompatibilidad de claves heredadas a nivel raíz.
    """
    if isinstance(orig_data, dict) and "error" in orig_data:
        return orig_data

    error_code = getattr(exc, "default_code", None)
    error_message = ""
    details: Dict[str, Any] = {}

    if exc:
        if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
            error_code = ErrorCode.AUTH_INVALID
            error_message = "Credenciales de autenticación no proporcionadas o inválidas."
        elif isinstance(exc, exceptions.PermissionDenied):
            msg_str = str(exc.detail if hasattr(exc, "detail") else exc)
            if any(w in msg_str.lower() for w in ("bloqueo", "silenciado", "muted", "interactuar")):
                error_code = ErrorCode.USER_BLOCKED
                error_message = msg_str
            else:
                error_code = ErrorCode.PERMISSION_DENIED
                error_message = msg_str or "No tienes permiso para realizar esta acción."
        elif isinstance(exc, exceptions.NotFound):
            error_code = ErrorCode.NOT_FOUND
            error_message = "El recurso solicitado no fue encontrado."
        elif isinstance(exc, exceptions.MethodNotAllowed):
            error_code = ErrorCode.METHOD_NOT_ALLOWED
            error_message = f"Método {method} no permitido." if method else "Método no permitido."
        elif isinstance(exc, exceptions.Throttled):
            error_code = ErrorCode.RATE_LIMITED
            wait_seconds = getattr(exc, "wait", None)
            error_message = (
                f"Petición limitada por tasa de uso. Disponible en {int(wait_seconds)} segundos."
                if wait_seconds
                else "Petición limitada por tasa de uso."
            )
        elif isinstance(exc, (ReviewAlreadyExistsError, BookDuplicateError, UserBlockedError, RateLimitedError)):
            error_code = getattr(exc, "default_code", ErrorCode.VALIDATION_ERROR)
            error_message = str(exc.detail if hasattr(exc, "detail") else exc)

    # Extraer detalles específicos y mensaje si existe 'detail'
    if isinstance(orig_data, dict):
        if "detail" in orig_data:
            detail_val = orig_data["detail"]
            if isinstance(detail_val, str):
                error_message = detail_val
            elif isinstance(detail_val, list) and detail_val:
                error_message = str(detail_val[0])
            details = {k: v for k, v in orig_data.items() if k != "detail"}
        else:
            details = orig_data
            if not error_message and details:
                first_key = next(iter(details))
                first_val = details[first_key]
                first_text = first_val[0] if isinstance(first_val, list) and first_val else str(first_val)
                error_message = f"{first_key}: {first_text}"
    elif isinstance(orig_data, list):
        details = {"errors": orig_data}
        if orig_data:
            error_message = str(orig_data[0])

    # Deducción por mensaje y status_code si el código aún no fue fijado
    msg_lower = error_message.lower()
    if not error_code or str(error_code).lower() in ("invalid", "error"):
        if status_code == 401:
            error_code = ErrorCode.AUTH_INVALID
        elif status_code == 403:
            if any(w in msg_lower for w in ("bloqueo", "silenciado", "muted", "interactuar")):
                error_code = ErrorCode.USER_BLOCKED
            else:
                error_code = ErrorCode.PERMISSION_DENIED
        elif status_code == 404:
            error_code = ErrorCode.NOT_FOUND
        elif status_code == 405:
            error_code = ErrorCode.METHOD_NOT_ALLOWED
        elif status_code == 429:
            error_code = ErrorCode.RATE_LIMITED
        elif status_code in (400, 409):
            if any(w in msg_lower for w in ("reseña", "review")):
                error_code = ErrorCode.REVIEW_ALREADY_EXISTS
            elif any(w in msg_lower for w in ("duplicat", "ya existe un libro", "isbn")):
                error_code = ErrorCode.BOOK_DUPLICATE
            elif any(w in msg_lower for w in ("bloqueo", "silenciad")):
                error_code = ErrorCode.USER_BLOCKED
            else:
                error_code = ErrorCode.VALIDATION_ERROR
        elif status_code >= 500:
            error_code = ErrorCode.INTERNAL_SERVER_ERROR
        else:
            error_code = ErrorCode.VALIDATION_ERROR

    if not error_message:
        error_message = "Ha ocurrido un error en la solicitud."

    unified_error_block = {
        "code": str(error_code),
        "message": str(error_message),
        "details": details,
    }

    new_data: Dict[str, Any] = {"error": unified_error_block}
    if isinstance(orig_data, dict):
        for k, v in orig_data.items():
            new_data[k] = v
        if "detail" not in new_data:
            new_data["detail"] = error_message
    elif isinstance(orig_data, list):
        new_data["detail"] = error_message
        new_data["errors"] = orig_data
    else:
        new_data["detail"] = str(orig_data)

    return new_data


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response | None:
    """
    Manejador unificado de excepciones para Django REST Framework.
    """
    response = drf_exception_handler(exc, context)

    if response is None:
        logger.error(f"Excepción interna no manejada en {context.get('view')}: {exc}", exc_info=True)
        return Response(
            {
                "error": {
                    "code": ErrorCode.INTERNAL_SERVER_ERROR,
                    "message": "Ha ocurrido un error interno en el servidor.",
                    "details": {},
                },
                "detail": "Ha ocurrido un error interno en el servidor.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    method = ""
    req = context.get("request")
    if req and hasattr(req, "method"):
        method = req.method

    response.data = normalize_error_data(response.data, response.status_code, exc=exc, method=method)
    return response

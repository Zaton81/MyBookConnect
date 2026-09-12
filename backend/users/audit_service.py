"""
Servicio centralizado para el registro de eventos de auditoría (Fase 30).

Garantiza:
- Captura homogénea de actor, IP, User-Agent y metadatos contextuales.
- Relación polimórfica (GenericForeignKey) con el objeto afectado.
- Registro textual inmutable (target_repr) resistente a eliminaciones posteriores.
- Tolerancia a fallos: errores en el log nunca abortan la operación de negocio.
"""

import logging
from typing import Any, Optional

from django.contrib.contenttypes.models import ContentType
from django.db import models

from .models import AuditAction, AuditLog

logger = logging.getLogger(__name__)


def _extract_client_ip(request) -> Optional[str]:
    """Obtiene la IP remota del cliente respetando proxies inversos."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _build_target_repr(target: Any) -> str:
    """Genera una representación textual representativa del objeto afectado."""
    if not target:
        return ""

    model_name = target.__class__.__name__

    if model_name == 'User':
        return f"Usuario @{getattr(target, 'username', '')} (id={getattr(target, 'id', '')})"
    elif model_name == 'Review':
        author = getattr(getattr(target, 'user', None), 'username', 'desconocido')
        book_title = getattr(getattr(target, 'book', None), 'title', 'libro')
        return f"Reseña #{getattr(target, 'id', '')} por @{author} en '{book_title}'"
    elif model_name == 'ReviewComment':
        author = getattr(getattr(target, 'user', None), 'username', 'desconocido')
        return f"Comentario #{getattr(target, 'id', '')} por @{author}"
    elif model_name == 'Message':
        sender = getattr(getattr(target, 'sender', None), 'username', 'desconocido')
        return f"Mensaje #{getattr(target, 'id', '')} de @{sender}"
    elif model_name == 'Report':
        return f"Reporte #{getattr(target, 'id', '')} ({getattr(target, 'reason', '')})"
    elif model_name == 'Book':
        return f"Libro #{getattr(target, 'id', '')} '{getattr(target, 'title', '')}'"
    elif model_name == 'Author':
        return f"Autor #{getattr(target, 'id', '')} '{getattr(target, 'name', '')}'"

    return str(target)[:255]


def log_audit(
    action: str | AuditAction,
    actor: Optional[Any] = None,
    target: Optional[Any] = None,
    request: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> Optional[AuditLog]:
    """
    Registra de forma segura un evento sensible en la bitácora inmutable de auditoría.

    Args:
        action: Constante de AuditAction o cadena descriptiva.
        actor: Usuario que ejecuta la acción. Si es None y hay request, se extrae de request.user.
        target: Instancia de modelo afectada por la acción.
        request: HttpRequest opcional para extraer actor, IP y User-Agent automáticamente.
        ip_address: IP explícita en caso de no provenir de request.
        user_agent: User-Agent explícito en caso de no provenir de request.
        metadata: Diccionario con detalles contextuales adicionales.

    Returns:
        Instancia de AuditLog creada o None en caso de omisión/error.
    """
    try:
        # Resolver actor
        if actor is None and request:
            req_user = getattr(request, 'user', None)
            if req_user and getattr(req_user, 'is_authenticated', False):
                actor = req_user

        # Resolver IP y User-Agent
        if request:
            if not ip_address:
                ip_address = _extract_client_ip(request)
            if not user_agent:
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:512]

        # Resolver objeto objetivo
        content_type = None
        object_id = None
        target_repr = ""

        if target and isinstance(target, models.Model):
            content_type = ContentType.objects.get_for_model(target)
            object_id = getattr(target, 'pk', None)
            target_repr = _build_target_repr(target)
        elif target:
            target_repr = str(target)[:255]

        audit_entry = AuditLog.objects.create(
            actor=actor,
            action=str(action),
            content_type=content_type,
            object_id=object_id,
            target_repr=target_repr,
            ip_address=ip_address,
            user_agent=user_agent or "",
            metadata=metadata or {},
        )
        return audit_entry
    except Exception as exc:
        logger.warning(f"Error registrando entrada de auditoría [{action}]: {exc}", exc_info=True)
        return None

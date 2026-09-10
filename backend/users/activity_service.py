import logging
from typing import Any

from .models import Activity, ActivityType

logger = logging.getLogger(__name__)


def record_activity(
    user,
    activity_type: str | ActivityType,
    book=None,
    review=None,
    target_user=None,
    metadata: dict[str, Any] | None = None,
) -> Activity | None:
    """
    Registra de forma segura un evento de actividad en el feed social.
    Garantiza que errores en el registro nunca bloqueen el flujo principal del usuario.
    """
    try:
        if not user or not getattr(user, 'is_authenticated', False):
            return None

        activity = Activity.objects.create(
            user=user,
            type=activity_type,
            book=book,
            review=review,
            target_user=target_user,
            metadata=metadata or {},
        )
        return activity
    except Exception as exc:
        logger.warning(f"Error registrando actividad ({activity_type}) para {user}: {exc}")
        return None

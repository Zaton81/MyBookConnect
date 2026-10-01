"""
Tareas Celery para registro asíncrono y agregación de eventos de analítica (Fase 26).
"""

import logging

from celery import shared_task
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def record_analytics_event_task(
    self,
    event_type: str,
    user_id: int | None = None,
    session_id: str = '',
    metadata: dict | None = None,
) -> bool:
    """
    Tarea Celery para registrar eventos de analítica de producto en segundo plano.
    """
    try:
        from analytics.services import AnalyticsService

        user = None
        if user_id:
            user = User.objects.filter(id=user_id).first()

        AnalyticsService.track_event(
            event_type=event_type,
            user=user,
            session_id=session_id,
            metadata=metadata,
        )
        return True
    except Exception as exc:
        logger.warning("Error en record_analytics_event_task (%s): %s", event_type, exc)
        raise self.retry(exc=exc) from exc

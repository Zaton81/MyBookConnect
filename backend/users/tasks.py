"""
Tareas Celery para la gestión asíncrona de usuarios y comunicaciones (Fase 30 — Escalabilidad).
Enrutadas a la cola dedicada 'emails' para evitar bloqueos en el hilo HTTP y aislar
los tiempos de respuesta de servidores SMTP externos.
"""
import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_transactional_email_task(
    self,
    subject: str,
    message: str,
    recipient_list: list[str],
    html_message: str | None = None,
    from_email: str | None = None,
) -> bool:
    """
    Envía correos transaccionales (confirmación de registro, reseteo de contraseña,
    verificación de email) de forma desacoplada y asíncrona.
    """
    sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mybookconnect.com')
    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=sender,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"send_transactional_email_task: Correo '{subject}' enviado a {recipient_list} (estado: {sent})")
        return bool(sent)
    except Exception as exc:
        logger.warning(f"Error al enviar correo transaccional '{subject}' a {recipient_list}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_notification_email_task(
    self,
    recipient_email: str,
    subject: str,
    message: str,
    notification_id: int | None = None,
    html_message: str | None = None,
) -> bool:
    """
    Envía notificaciones sociales o de actividad por correo electrónico de forma asíncrona.
    """
    sender = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@mybookconnect.com')
    try:
        sent = send_mail(
            subject=subject,
            message=message,
            from_email=sender,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(
            f"send_notification_email_task: Notificación #{notification_id} enviada a {recipient_email}"
        )
        return bool(sent)
    except Exception as exc:
        logger.warning(
            f"Error al enviar notificación #{notification_id} por email a {recipient_email}: {exc}"
        )
        raise self.retry(exc=exc) from exc

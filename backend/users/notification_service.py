import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification, NotificationPreference, NotificationType
from .privacy_service import PrivacyService

logger = logging.getLogger(__name__)

TYPE_PREFERENCE_MAP = {
    NotificationType.FOLLOW: ('in_app_follow', 'email_follow'),
    NotificationType.FOLLOW_ACCEPTED: ('in_app_follow_accepted', 'email_follow_accepted'),
    NotificationType.LIKE: ('in_app_like', 'email_like'),
    NotificationType.COMMENT: ('in_app_comment', 'email_comment'),
    NotificationType.REPLY: ('in_app_reply', 'email_reply'),
    NotificationType.LIST_FOLLOW: ('in_app_list', 'email_list'),
    NotificationType.MESSAGE: ('in_app_message', 'email_message'),
    NotificationType.RECOMMENDATION: ('in_app_recommendation', 'email_recommendation'),
}


class NotificationService:
    @staticmethod
    def get_or_create_preferences(user) -> NotificationPreference:
        """Obtiene o inicializa con valores por defecto las preferencias de notificación."""
        prefs, _ = NotificationPreference.objects.get_or_create(user=user)
        return prefs

    @classmethod
    def send_notification(
        cls,
        recipient,
        actor=None,
        notif_type: str | NotificationType = NotificationType.SYSTEM,
        title: str = '',
        message: str = '',
        link: str = '',
    ) -> Notification | None:
        """
        Emite una notificación validando políticas de privacidad (bloqueos y silencios)
        y preferencias de canal del destinatario (In-App y Email).
        """
        try:
            if not recipient or not getattr(recipient, 'is_authenticated', False):
                return None

            # Un usuario no se auto-notifica de sus propias acciones
            if actor and actor.id == recipient.id:
                return None

            # 1. Reglas de Privacidad: bloqueos bidireccionales y silenciados
            if actor:
                if PrivacyService.are_mutually_blocked(recipient, actor):
                    return None
                if recipient.muted_users.filter(id=actor.id).exists():
                    return None

            # 2. Cargar preferencias del destinatario
            prefs = cls.get_or_create_preferences(recipient)
            in_app_pref_name, email_pref_name = TYPE_PREFERENCE_MAP.get(notif_type, (None, None))

            in_app_enabled = getattr(prefs, in_app_pref_name, True) if in_app_pref_name else True
            email_enabled = getattr(prefs, email_pref_name, False) if email_pref_name else False

            notification = None

            # 3. Canal In-App
            if in_app_enabled:
                notification = Notification.objects.create(
                    recipient=recipient,
                    actor=actor,
                    type=notif_type,
                    title=title,
                    message=message,
                    link=link,
                )

            # 4. Canal Email (opcional según preferencia)
            if email_enabled and recipient.email:
                cls._dispatch_email_notification(recipient, title, message, link)

            return notification

        except Exception as exc:
            logger.warning(f"Error despachando notificación ({notif_type}) para {recipient}: {exc}")
            return None

    @staticmethod
    def _dispatch_email_notification(recipient, title: str, message: str, link: str):
        """Envía el correo transaccional de forma segura y tolerante a fallos."""
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@mybookconnect.com')
            full_content = f"{title}\n\n{message}\n\nPuedes ver los detalles aquí: {link}"
            send_mail(
                subject=f"[MyBookConnect] {title}",
                message=full_content,
                from_email=from_email,
                recipient_list=[recipient.email],
                fail_silently=True,
            )
        except Exception as mail_exc:
            logger.warning(f"Fallo al enviar notificación por correo a {recipient.email}: {mail_exc}")

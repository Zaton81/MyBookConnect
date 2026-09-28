"""
Servicios de analítica de producto, cálculo de embudos y telemetría de eventos (Fase 26).
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from analytics.models import ProductAnalyticsEvent, ProductEventType

logger = logging.getLogger(__name__)
User = get_user_model()


def hash_ip_address(ip: str | None) -> str:
    """
    Genera un hash SHA256 truncado (primeros 16 caracteres) de la IP para
    disociar visitas sin almacenar datos personales según normativas RGPD.
    """
    if not ip or ip in ('127.0.0.1', 'localhost', 'desconocida'):
        return ''
    salt = "mybookconnect_analytics_salt"
    return hashlib.sha256(f"{salt}_{ip}".encode('utf-8')).hexdigest()[:16]


class AnalyticsService:
    @staticmethod
    def track_event(
        event_type: str,
        user: Any = None,
        session_id: str = '',
        metadata: dict[str, Any] | None = None,
        request: Any = None,
    ) -> ProductAnalyticsEvent:
        """
        Registra un evento de producto garantizando sanitización de metadatos.

        :param event_type: Tipo canónico de evento (ProductEventType).
        :param user: Instancia de usuario si está autenticado.
        :param session_id: Token disociado de sesión para visitas pre-login.
        :param metadata: Diccionario con datos contextuales cuantitativos (book_id, source, etc.).
        :param request: Objeto HttpRequest opcional para extraer IP anonimizada y sesión.
        :return: Instancia persistida de ProductAnalyticsEvent.
        """
        if event_type not in ProductEventType.values:
            raise ValueError(f"Tipo de evento '{event_type}' no reconocido en ProductEventType.")

        meta = dict(metadata or {})
        # Evitar inadvertidamente persistir campos sensibles
        forbidden_keys = {'password', 'token', 'authorization', 'secret', 'credit_card', 'email'}
        sanitized_meta = {k: v for k, v in meta.items() if k.lower() not in forbidden_keys}

        ip_str = ''
        extracted_session = session_id or ''
        target_user = user

        if request:
            if not target_user and getattr(request, 'user', None) and request.user.is_authenticated:
                target_user = request.user
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            if client_ip:
                ip_str = client_ip.split(',')[0].strip()
            if not extracted_session and hasattr(request, 'session') and request.session.session_key:
                extracted_session = request.session.session_key

        ip_h = hash_ip_address(ip_str)

        event = ProductAnalyticsEvent.objects.create(
            event_type=event_type,
            user=target_user if (target_user and getattr(target_user, 'is_authenticated', False)) else None,
            session_id=extracted_session[:64],
            metadata=sanitized_meta,
            ip_hash=ip_h,
        )
        return event

    @staticmethod
    def get_event_summary(
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Calcula el resumen cuantitativo de eventos agrupados por tipo.
        """
        qs = ProductAnalyticsEvent.objects.all()
        if start_date:
            qs = qs.filter(timestamp__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__lte=end_date)

        counts = {choice[0]: 0 for choice in ProductEventType.choices}
        for item in qs.values('event_type').annotate(total=Count('id')):
            counts[item['event_type']] = item['total']

        total_events = sum(counts.values())
        unique_users = qs.filter(user__isnull=False).values('user').distinct().count()

        return {
            "total_events": total_events,
            "unique_active_users": unique_users,
            "events_by_type": counts,
        }

    @staticmethod
    def get_funnel_metrics(
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Calcula las etapas del embudo de conversión y ciclo de vida de producto:
        visit -> signup -> activation -> retention -> social interaction -> reading activity.
        """
        qs = ProductAnalyticsEvent.objects.all()
        if start_date:
            qs = qs.filter(timestamp__gte=start_date)
        if end_date:
            qs = qs.filter(timestamp__lte=end_date)

        # 1. Visitas (Sesiones únicas o eventos book_view de usuarios anónimos + registrados)
        total_visits = (
            qs.filter(event_type__in=[ProductEventType.BOOK_VIEW, ProductEventType.LOGIN])
            .values('session_id')
            .distinct()
            .count()
            or qs.filter(event_type=ProductEventType.BOOK_VIEW).count()
        )

        # 2. Signups (Nuevos registros)
        signup_events = qs.filter(event_type=ProductEventType.SIGNUP)
        signups_count = signup_events.count()
        signup_user_ids = set(signup_events.values_list('user_id', flat=True))

        # 3. Activación (Usuarios registrados que han añadido al menos un libro o iniciado lectura)
        activation_user_ids = set(
            qs.filter(
                event_type__in=[ProductEventType.BOOK_ADDED, ProductEventType.READING_STARTED],
                user__isnull=False,
            ).values_list('user_id', flat=True)
        )
        activated_signups = len(signup_user_ids.intersection(activation_user_ids)) if signup_user_ids else len(activation_user_ids)

        # 4. Retención (Usuarios con actividad recurrente tras 7 días de registro)
        retention_candidates = 0
        now = timezone.now()
        for u in User.objects.filter(id__in=signup_user_ids):
            days_since_joined = (now - u.date_joined).days
            if days_since_joined >= 7:
                has_recent_activity = qs.filter(
                    user=u,
                    timestamp__gte=u.date_joined + timedelta(days=7),
                ).exists()
                if has_recent_activity:
                    retention_candidates += 1

        # 5. Interacción Social (Usuarios con reseñas, seguimientos, listas creadas o mensajes)
        social_users_count = (
            qs.filter(
                event_type__in=[
                    ProductEventType.REVIEW_CREATED,
                    ProductEventType.FOLLOW_CREATED,
                    ProductEventType.LIST_CREATED,
                    ProductEventType.MESSAGE_SENT,
                ],
                user__isnull=False,
            )
            .values('user')
            .distinct()
            .count()
        )

        # 6. Actividad de Lectura (Usuarios que han completado lecturas)
        readers_completed_count = (
            qs.filter(
                event_type=ProductEventType.READING_FINISHED,
                user__isnull=False,
            )
            .values('user')
            .distinct()
            .count()
        )

        # Ratios de conversión de embudo
        safe_visits = max(1, total_visits)
        safe_signups = max(1, signups_count)
        safe_activations = max(1, activated_signups)

        return {
            "funnel_steps": {
                "visits": total_visits,
                "signups": signups_count,
                "activations": activated_signups,
                "retained_7d": retention_candidates,
                "social_interaction": social_users_count,
                "reading_completed": readers_completed_count,
            },
            "conversion_rates": {
                "visit_to_signup_pct": round((signups_count / safe_visits) * 100, 2),
                "signup_to_activation_pct": round((activated_signups / safe_signups) * 100, 2),
                "activation_to_reading_completed_pct": round((readers_completed_count / safe_activations) * 100, 2),
            },
        }

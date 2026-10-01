"""
Servicio de métricas y telemetría operativa para la cohorte de Beta Cerrada (Fase 36).
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone

from .models import (
    BetaFeedback,
    BetaFeedbackStatus,
    BetaInvitation,
    SupportTicket,
    SupportTicketPriority,
    SupportTicketStatus,
)

User = get_user_model()


class BetaMetricsService:
    @classmethod
    def get_cohort_summary_metrics(cls) -> dict:
        """
        Calcula un resumen consolidado de las métricas clave de la beta cerrada:
        - Tasa de activación de invitaciones
        - Desglose de feedback por categoría y estado
        - Desglose de tickets de soporte por prioridad y estado
        - Actividad reciente de evaluadores
        """
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)

        # 1. Métricas de Invitaciones y Activación
        total_invitations = BetaInvitation.objects.count()
        active_invitations = BetaInvitation.objects.filter(is_active=True).count()
        used_invitations = BetaInvitation.objects.filter(uses_count__gt=0).count()
        total_uses = BetaInvitation.objects.aggregate(total=Sum('uses_count'))['total'] or 0

        activation_rate_pct = (
            round((used_invitations / total_invitations) * 100, 2)
            if total_invitations > 0
            else 0.0
        )

        # 2. Métricas de Feedback
        total_feedback = BetaFeedback.objects.count()
        feedback_by_category = dict(
            BetaFeedback.objects.values_list('category').annotate(count=Count('id'))
        )
        feedback_by_status = dict(
            BetaFeedback.objects.values_list('status').annotate(count=Count('id'))
        )
        unresolved_feedback_count = BetaFeedback.objects.filter(
            status__in=[BetaFeedbackStatus.NEW, BetaFeedbackStatus.IN_REVIEW]
        ).count()

        # 3. Métricas de Soporte
        total_tickets = SupportTicket.objects.count()
        tickets_by_priority = dict(
            SupportTicket.objects.values_list('priority').annotate(count=Count('id'))
        )
        tickets_by_status = dict(
            SupportTicket.objects.values_list('status').annotate(count=Count('id'))
        )
        critical_open_tickets_count = SupportTicket.objects.filter(
            priority__in=[SupportTicketPriority.CRITICAL, SupportTicketPriority.HIGH],
            status__in=[SupportTicketStatus.OPEN, SupportTicketStatus.IN_PROGRESS],
        ).count()

        # 4. Evaluadores activos
        active_feedback_users = set(
            BetaFeedback.objects.filter(
                created_at__gte=seven_days_ago, user__isnull=False
            ).values_list('user_id', flat=True)
        )
        active_ticket_users = set(
            SupportTicket.objects.filter(
                created_at__gte=seven_days_ago, user__isnull=False
            ).values_list('user_id', flat=True)
        )
        active_evaluators_count = len(active_feedback_users | active_ticket_users)

        # 5. Métricas de Retención D1 / D7 / D30 (Fase 37)
        try:
            from analytics.services import AnalyticsService
            retention_data = AnalyticsService.get_retention_metrics(days=30)
        except Exception:
            retention_data = {
                'timeframe_days': 30,
                'total_signups': 0,
                'd1_active_users': 0,
                'd1_retention_rate': 0.0,
                'd7_active_users': 0,
                'd7_retention_rate': 0.0,
                'd30_active_users': 0,
                'd30_retention_rate': 0.0,
            }

        return {
            'invitations': {
                'total': total_invitations,
                'active': active_invitations,
                'used': used_invitations,
                'total_uses': total_uses,
                'activation_rate_pct': activation_rate_pct,
            },
            'feedback': {
                'total': total_feedback,
                'unresolved': unresolved_feedback_count,
                'by_category': feedback_by_category,
                'by_status': feedback_by_status,
            },
            'support': {
                'total': total_tickets,
                'critical_or_high_open': critical_open_tickets_count,
                'by_priority': tickets_by_priority,
                'by_status': tickets_by_status,
            },
            'evaluators': {
                'active_last_7_days': active_evaluators_count,
            },
            'retention': retention_data,
            'generated_at': now.isoformat(),
        }


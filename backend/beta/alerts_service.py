"""
Servicio de detección y triaje de alertas de incidencias críticas para la Beta Cerrada (Fase 36).
"""

import logging

from .models import (
    BetaFeedback,
    BetaFeedbackCategory,
    BetaFeedbackStatus,
    SupportTicket,
    SupportTicketPriority,
    SupportTicketStatus,
)

logger = logging.getLogger('mybookconnect.observability')


class BetaAlertsService:
    @classmethod
    def process_feedback_submission(cls, feedback: BetaFeedback) -> bool:
        """
        Evalúa si el feedback recibido constituye una incidencia crítica o bloqueo.
        Retorna True si disparó una alerta.
        """
        if feedback.category == BetaFeedbackCategory.BUG:
            user_ident = feedback.user.username if feedback.user else 'Anonymous'
            logger.warning(
                "BETA_ALERT [BUG Report #%s]: %s (reportado por %s)",
                feedback.id,
                feedback.title,
                user_ident,
                extra={
                    'alert_type': 'beta_bug',
                    'feedback_id': feedback.id,
                    'user_id': feedback.user_id,
                    'category': feedback.category,
                },
            )
            return True
        return False

    @classmethod
    def process_support_ticket_submission(cls, ticket: SupportTicket) -> bool:
        """
        Evalúa si el ticket de soporte requiere atención inmediata (severidad alta o crítica).
        Retorna True si disparó una alerta.
        """
        if ticket.priority in (SupportTicketPriority.CRITICAL, SupportTicketPriority.HIGH):
            user_ident = ticket.user.username if ticket.user else 'Anonymous'
            level = logging.ERROR if ticket.priority == SupportTicketPriority.CRITICAL else logging.WARNING
            logger.log(
                level,
                "BETA_ALERT [Support Ticket #%s - %s]: %s (de %s)",
                ticket.id,
                ticket.priority.upper(),
                ticket.subject,
                user_ident,
                extra={
                    'alert_type': 'beta_urgent_support',
                    'ticket_id': ticket.id,
                    'priority': ticket.priority,
                    'user_id': ticket.user_id,
                },
            )
            return True
        return False

    @classmethod
    def get_active_alerts(cls) -> list[dict]:
        """
        Recopila todas las incidencias críticas pendientes de resolución para el triaje administrativo.
        """
        alerts = []

        # 1. Bugs no resueltos
        critical_bugs = BetaFeedback.objects.filter(
            category=BetaFeedbackCategory.BUG,
            status__in=[BetaFeedbackStatus.NEW, BetaFeedbackStatus.IN_REVIEW],
        ).select_related('user').order_by('-created_at')

        for item in critical_bugs:
            alerts.append({
                'id': f"feedback-{item.id}",
                'type': 'BUG',
                'severity': 'HIGH',
                'title': item.title,
                'description': item.description,
                'status': item.status,
                'user': item.user.username if item.user else 'Anonymous',
                'created_at': item.created_at.isoformat(),
                'url': item.page_url,
            })

        # 2. Tickets urgentes o críticos abiertos
        urgent_tickets = SupportTicket.objects.filter(
            priority__in=[SupportTicketPriority.CRITICAL, SupportTicketPriority.HIGH],
            status__in=[SupportTicketStatus.OPEN, SupportTicketStatus.IN_PROGRESS],
        ).select_related('user').order_by('-created_at')

        for item in urgent_tickets:
            alerts.append({
                'id': f"ticket-{item.id}",
                'type': 'SUPPORT_TICKET',
                'severity': item.priority.upper(),
                'title': item.subject,
                'description': item.message,
                'status': item.status,
                'user': item.user.username if item.user else 'Anonymous',
                'created_at': item.created_at.isoformat(),
                'url': f"/admin/support/{item.id}/",
            })

        # Ordenar por fecha más reciente
        alerts.sort(key=lambda a: a['created_at'], reverse=True)
        return alerts

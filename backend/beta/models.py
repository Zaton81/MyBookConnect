import secrets
from django.conf import settings
from django.db import models
from django.utils import timezone


class BetaFeedbackCategory(models.TextChoices):
    BUG = 'bug', 'Bug'
    CONFUSING_UX = 'confusing_ux', 'Confusing UX'
    MISSING_FEATURE = 'missing_feature', 'Missing Feature'
    PERFORMANCE = 'performance', 'Performance'
    PRIVACY_CONCERN = 'privacy_concern', 'Privacy Concern'
    RECOMMENDATION_QUALITY = 'recommendation_quality', 'Recommendation Quality'
    GENERAL_FEEDBACK = 'general_feedback', 'General Feedback'


class BetaFeedbackStatus(models.TextChoices):
    NEW = 'new', 'New'
    IN_REVIEW = 'in_review', 'In Review'
    RESOLVED = 'resolved', 'Resolved'
    DISMISSED = 'dismissed', 'Dismissed'


class BetaFeedback(models.Model):
    """
    Captura de feedback estructurado de los usuarios de la beta cerrada.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='beta_feedback_entries'
    )
    category = models.CharField(
        max_length=40,
        choices=BetaFeedbackCategory.choices,
        default=BetaFeedbackCategory.GENERAL_FEEDBACK,
        db_index=True
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    page_url = models.CharField(max_length=500, blank=True, default='')
    device_info = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(
        max_length=20,
        choices=BetaFeedbackStatus.choices,
        default=BetaFeedbackStatus.NEW,
        db_index=True
    )
    admin_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Beta Feedback'
        verbose_name_plural = 'Beta Feedbacks'

    def __str__(self):
        user_ident = self.user.username if self.user else 'Anonymous/Deleted'
        return f"[{self.category}] {self.title[:50]} by {user_ident}"


class BetaInvitation(models.Model):
    """
    Gestión de códigos de invitación únicos para la cohorte de beta cerrada.
    """
    code = models.CharField(max_length=32, unique=True, db_index=True)
    invited_email = models.EmailField(blank=True, default='')
    max_uses = models.PositiveIntegerField(default=1)
    uses_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_beta_invitations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Beta Invitation'
        verbose_name_plural = 'Beta Invitations'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = secrets.token_urlsafe(16)[:32]
        super().save(*args, **kwargs)

    def is_valid(self) -> bool:
        if not self.is_active:
            return False
        if self.uses_count >= self.max_uses:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def use(self) -> bool:
        if not self.is_valid():
            return False
        self.uses_count += 1
        if self.uses_count >= self.max_uses:
            self.is_active = False
        self.save(update_fields=['uses_count', 'is_active'])
        return True

    def __str__(self):
        return f"Invitation {self.code} ({self.uses_count}/{self.max_uses})"


class SupportTicketCategory(models.TextChoices):
    ACCOUNT = 'account', 'Cuenta y Acceso'
    TECHNICAL = 'technical', 'Problema Técnico'
    CONTENT = 'content', 'Contenido o Catálogo'
    OTHER = 'other', 'Otro'


class SupportTicketStatus(models.TextChoices):
    OPEN = 'open', 'Abierto'
    IN_PROGRESS = 'in_progress', 'En Proceso'
    RESOLVED = 'resolved', 'Resuelto'
    CLOSED = 'closed', 'Cerrado'


class SupportTicketPriority(models.TextChoices):
    LOW = 'low', 'Baja'
    MEDIUM = 'medium', 'Media'
    HIGH = 'high', 'Alta'
    CRITICAL = 'critical', 'Crítica'


class SupportTicket(models.Model):
    """
    Canal de soporte formal para los usuarios de la beta abierta (Fase 28).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets'
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=SupportTicketCategory.choices,
        default=SupportTicketCategory.TECHNICAL,
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=SupportTicketStatus.choices,
        default=SupportTicketStatus.OPEN,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=SupportTicketPriority.choices,
        default=SupportTicketPriority.MEDIUM,
        db_index=True
    )
    admin_response = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Support Ticket'
        verbose_name_plural = 'Support Tickets'

    def __str__(self):
        user_ident = self.user.username if self.user else 'Anonymous/Deleted'
        return f"Ticket #{self.id} [{self.category}/{self.status}] {self.subject[:40]} ({user_ident})"

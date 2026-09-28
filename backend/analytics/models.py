"""
Modelos de datos para telemetría de eventos de producto y métricas de embudo (Fase 26).
Diseñado respetando la privacidad del usuario (sin PII, IP anonimizada y SET_NULL ante supresión).
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class ProductEventType(models.TextChoices):
    # Autenticación y Visitas
    SIGNUP = 'signup', 'Registro de Usuario'
    LOGIN = 'login', 'Inicio de Sesión'

    # Interacción de Catálogo y Lectura
    BOOK_VIEW = 'book_view', 'Visualización de Libro'
    BOOK_ADDED = 'book_added', 'Libro Añadido a Biblioteca'
    READING_STARTED = 'reading_started', 'Lectura Iniciada'
    READING_FINISHED = 'reading_finished', 'Lectura Finalizada'

    # Social y Comunidad
    REVIEW_CREATED = 'review_created', 'Reseña Creada'
    FOLLOW_CREATED = 'follow_created', 'Usuario Seguido'
    LIST_CREATED = 'list_created', 'Lista Creada'
    MESSAGE_SENT = 'message_sent', 'Mensaje Enviado'

    # Recomendaciones y Descubrimiento
    RECOMMENDATION_SHOWN = 'recommendation_shown', 'Recomendación Mostrada'
    RECOMMENDATION_CLICKED = 'recommendation_clicked', 'Recomendación Clickeada'
    RECOMMENDATION_DISMISSED = 'recommendation_dismissed', 'Recomendación Descartada'


class ProductAnalyticsEvent(models.Model):
    """
    Registro individual de telemetría de producto.
    Preserva datos cuantitativos sin comprometer la identidad personal tras la baja de la cuenta.
    """
    event_type = models.CharField(
        max_length=40,
        choices=ProductEventType.choices,
        db_index=True,
        verbose_name="Tipo de evento",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events',
        verbose_name="Usuario (si está autenticado)",
    )
    session_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        db_index=True,
        verbose_name="Identificador disociado de sesión",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Metadatos cuantitativos contextuales",
    )
    ip_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        verbose_name="Hash criptográfico disociado de IP (sin PII)",
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Fecha y hora del evento",
    )

    class Meta:
        verbose_name = "Evento de Analítica de Producto"
        verbose_name_plural = "Eventos de Analítica de Producto"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['event_type', 'timestamp'], name='idx_pae_type_time'),
            models.Index(fields=['user', 'timestamp'], name='idx_pae_user_time'),
            models.Index(fields=['session_id', 'timestamp'], name='idx_pae_sess_time'),
        ]

    def __str__(self) -> str:
        u_info = f"@{self.user.username}" if self.user else f"anon[{self.session_id[:8]}]"
        return f"[{self.event_type}] {u_info} ({self.timestamp:%Y-%m-%d %H:%M:%S})"

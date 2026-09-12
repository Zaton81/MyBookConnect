from datetime import date

from django.contrib.auth.models import AbstractUser
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from mybookconnect.media_security import validate_avatar_image


class PrivacyChoices(models.TextChoices):
    PUBLIC = 'public', 'Público'
    FRIENDS = 'friends', 'Solo amigos'
    PRIVATE = 'private', 'Privado'


class UserRole(models.TextChoices):
    """Jerarquía de roles del sistema (Fase 29)."""
    USER = 'USER', 'Usuario'
    EDITOR = 'EDITOR', 'Editor'
    MODERATOR = 'MODERATOR', 'Moderador'
    ADMIN = 'ADMIN', 'Administrador'


class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        validators=[validate_avatar_image],
        help_text="Imagen de avatar (JPEG, PNG, WebP; máx 5MB; dimensiones 50x50 a 6000x6000px)",
    )
    email = models.EmailField(unique=True, blank=False, null=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, related_name='blocked_by', blank=True)
    is_editor = models.BooleanField(default=False)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        db_index=True,
        help_text="Jerarquía y rol del usuario (USER, EDITOR, MODERATOR, ADMIN)",
    )

    birth_date = models.DateField(null=True, blank=True,
        validators=[MinValueValidator(limit_value=date(1900, 1, 1))])
    location = models.CharField(max_length=100, blank=True)
    privacy_level = models.CharField(
        max_length=10,
        choices=PrivacyChoices.choices,
        default=PrivacyChoices.PUBLIC
    )
    # Preferencias de visibilidad por campo (solo aplican cuando el perfil es público)
    show_email = models.BooleanField(default=False)
    show_birth_date = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    show_bio = models.BooleanField(default=True)

    class Meta:
        ordering = ['-date_joined']

    @property
    def is_moderator(self) -> bool:
        """Determina si el usuario tiene privilegios de moderación o administración."""
        return self.role in (UserRole.MODERATOR, UserRole.ADMIN) or self.is_staff or self.is_superuser

    @property
    def is_editor_user(self) -> bool:
        """Determina si el usuario tiene privilegios editoriales o superiores."""
        return self.is_editor or self.role in (UserRole.EDITOR, UserRole.MODERATOR, UserRole.ADMIN) or self.is_staff or self.is_superuser

    def save(self, *args, **kwargs):
        """Mantiene sincronizado el rol con banderas booleanas heredadas."""
        if (self.is_superuser or self.is_staff) and self.role == UserRole.USER:
            self.role = UserRole.ADMIN
        elif self.is_editor and self.role == UserRole.USER:
            self.role = UserRole.EDITOR
        elif self.role == UserRole.EDITOR and not self.is_editor:
            self.is_editor = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


class NotificationType(models.TextChoices):
    FOLLOW = 'FOLLOW', 'Nuevo seguidor'
    MESSAGE = 'MESSAGE', 'Nuevo mensaje'
    REVIEW = 'REVIEW', 'Nueva reseña'
    LIKE = 'LIKE', 'Me gusta en reseña'
    COMMENT = 'COMMENT', 'Comentario en reseña'
    SYSTEM = 'SYSTEM', 'Sistema'


class Notification(models.Model):
    recipient = models.ForeignKey(User, related_name='notifications', on_delete=models.CASCADE)
    actor = models.ForeignKey(User, related_name='sent_notifications', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.SYSTEM)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True, default='')
    link = models.CharField(max_length=255, blank=True, default='')
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'read'], name='idx_notif_recipient_read'),
            models.Index(fields=['recipient', 'created_at'], name='idx_notif_recipient_created'),
        ]

    def __str__(self):
        return f"Notificación para {self.recipient.username}: {self.title}"


class ActivityType(models.TextChoices):
    BOOK_ADDED = 'BOOK_ADDED', 'Libro añadido'
    BOOK_STARTED = 'BOOK_STARTED', 'Empezó a leer'
    BOOK_FINISHED = 'BOOK_FINISHED', 'Terminó de leer'
    BOOK_RATED = 'BOOK_RATED', 'Puntuó un libro'
    REVIEW_CREATED = 'REVIEW_CREATED', 'Publicó una reseña'
    USER_FOLLOWED = 'USER_FOLLOWED', 'Comenzó a seguir'
    LIST_CREATED = 'LIST_CREATED', 'Creó una lista'


class Activity(models.Model):
    user = models.ForeignKey(User, related_name='activities', on_delete=models.CASCADE)
    type = models.CharField(max_length=30, choices=ActivityType.choices, db_index=True)
    book = models.ForeignKey('books.Book', null=True, blank=True, on_delete=models.CASCADE, related_name='activities')
    review = models.ForeignKey('books.Review', null=True, blank=True, on_delete=models.CASCADE, related_name='activities')
    target_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE, related_name='target_activities')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_activity_user_created'),
            models.Index(fields=['-created_at'], name='idx_activity_created'),
            models.Index(fields=['type', '-created_at'], name='idx_activity_type_created'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_type_display()} ({self.created_at})"


class ReportStatus(models.TextChoices):
    OPEN = 'OPEN', 'Abierto'
    UNDER_REVIEW = 'UNDER_REVIEW', 'En revisión'
    RESOLVED = 'RESOLVED', 'Resuelto'
    REJECTED = 'REJECTED', 'Rechazado'


class ReportReason(models.TextChoices):
    SPAM = 'SPAM', 'Spam o publicidad no deseada'
    HARASSMENT = 'HARASSMENT', 'Acoso o intimidación'
    HATE_SPEECH = 'HATE_SPEECH', 'Incitación al odio o violencia'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Contenido explícito o inapropiado'
    SPOILER = 'SPOILER', 'Spoilers sin advertencia'
    COPYRIGHT = 'COPYRIGHT', 'Infracción de derechos de autor'
    OTHER = 'OTHER', 'Otro motivo'


class Report(models.Model):
    """
    Modelo de denuncias y moderación de contenido (Fase 29).
    Permite registrar denuncias de usuarios sobre:
    - Cuentas de usuario (User)
    - Reseñas (Review)
    - Comentarios en reseñas (ReviewComment)
    - Mensajes de chat (Message)
    """
    reporter = models.ForeignKey(
        User,
        related_name='filed_reports',
        on_delete=models.CASCADE,
        help_text="Usuario que realiza la denuncia",
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Modelo del objeto reportado",
    )
    object_id = models.PositiveIntegerField(db_index=True, help_text="ID primario del objeto reportado")
    content_object = GenericForeignKey('content_type', 'object_id')

    reason = models.CharField(
        max_length=30,
        choices=ReportReason.choices,
        default=ReportReason.OTHER,
        help_text="Motivo de la denuncia",
    )
    description = models.TextField(
        blank=True,
        help_text="Detalles adicionales proporcionados por el denunciante",
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
        db_index=True,
        help_text="Estado actual de la denuncia",
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text="Notas y justificación del moderador al resolver o rechazar",
    )
    action_taken = models.CharField(
        max_length=50,
        blank=True,
        help_text="Acción efectuada: HIDE_CONTENT, BAN_USER, DISMISS, WARNING",
    )
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='resolved_reports',
        on_delete=models.SET_NULL,
        help_text="Moderador o administrador que resolvió la denuncia",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='idx_report_status_created'),
            models.Index(fields=['content_type', 'object_id'], name='idx_report_content_obj'),
            models.Index(fields=['reporter', 'status'], name='idx_report_reporter_status'),
        ]

    def __str__(self):
        return f"Reporte #{self.id} ({self.get_status_display()}) por @{self.reporter.username}"


class AuditAction(models.TextChoices):
    ROLE_CHANGE = 'ROLE_CHANGE', 'Cambio de Rol'
    USER_BAN = 'USER_BAN', 'Bloqueo de Usuario'
    USER_UNBAN = 'USER_UNBAN', 'Desbloqueo de Usuario'
    USER_BLOCK = 'USER_BLOCK', 'Bloqueo Social entre Usuarios'
    USER_UNBLOCK = 'USER_UNBLOCK', 'Desbloqueo Social entre Usuarios'
    MODERATION_RESOLVE = 'MODERATION_RESOLVE', 'Resolución de Denuncia'
    MODERATION_REJECT = 'MODERATION_REJECT', 'Rechazo de Denuncia'
    CONTENT_DELETE = 'CONTENT_DELETE', 'Eliminación de Contenido'
    SECURITY_PASSWORD_CHANGE = 'SECURITY_PASSWORD_CHANGE', 'Cambio de Contraseña'
    OTHER = 'OTHER', 'Otra Acción'


class AuditLog(models.Model):
    """
    Registro inmutable de auditoría para trazabilidad de eventos sensibles (Fase 30).
    """
    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        related_name='audit_actions',
        on_delete=models.SET_NULL,
        help_text="Usuario que ejecutó la acción (o None para procesos del sistema)",
    )
    action = models.CharField(
        max_length=64,
        choices=AuditAction.choices,
        db_index=True,
        help_text="Identificador de la acción realizada",
    )
    content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
    )
    content_object = GenericForeignKey('content_type', 'object_id')
    target_repr = models.CharField(
        max_length=255,
        blank=True,
        help_text="Representación textual congelada del objeto afectado",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Dirección IP de origen",
    )
    user_agent = models.CharField(
        max_length=512,
        blank=True,
        help_text="User-Agent del cliente",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Información contextual estructurada adicional",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Marca temporal inmutable de la acción",
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', '-created_at'], name='idx_audit_action_created'),
            models.Index(fields=['content_type', 'object_id'], name='idx_audit_content_obj'),
            models.Index(fields=['actor', '-created_at'], name='idx_audit_actor_created'),
        ]

    def __str__(self):
        actor_name = self.actor.username if self.actor else "Sistema"
        return f"[{self.created_at:%Y-%m-%d %H:%M:%S}] {actor_name} -> {self.action} ({self.target_repr})"


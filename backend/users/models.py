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


class MessagePrivacyChoices(models.TextChoices):
    EVERYONE = 'everyone', 'Todos los usuarios'
    FOLLOWED = 'followed', 'Solo personas que sigo / amigos'
    NOBODY = 'nobody', 'Nadie'


class UserRole(models.TextChoices):
    """Jerarquía de roles del sistema (Fase 29)."""
    USER = 'USER', 'Usuario'
    EDITOR = 'EDITOR', 'Editor'
    MODERATOR = 'MODERATOR', 'Moderador'
    ADMIN = 'ADMIN', 'Administrador'


class AccountType(models.TextChoices):
    """Modos de cuenta en la comunidad: Lector, Escritor/Autor, o Ambos."""
    READER = 'reader', 'Lector'
    AUTHOR = 'author', 'Escritor / Autor'
    BOTH = 'both', 'Lector y Escritor'


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
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Indica si la dirección de correo electrónico ha sido confirmada.",
    )
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, related_name='blocked_by', blank=True)
    muted_users = models.ManyToManyField('self', symmetrical=False, related_name='muted_by', blank=True, help_text="Usuarios silenciados socialmente por este usuario (Fase 58).")
    muted_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Fecha y hora de finalización del silenciamiento disciplinario impuesto por moderación (Fase 58).",
    )
    is_editor = models.BooleanField(default=False)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        db_index=True,
        help_text="Jerarquía y rol del usuario (USER, EDITOR, MODERATOR, ADMIN)",
    )
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.READER,
        db_index=True,
        help_text="Modalidad de cuenta en la plataforma: lector, escritor/autor o ambos.",
    )


    birth_date = models.DateField(null=True, blank=True,
        validators=[MinValueValidator(limit_value=date(1900, 1, 1))])
    location = models.CharField(max_length=100, blank=True)
    privacy_level = models.CharField(
        max_length=10,
        choices=PrivacyChoices.choices,
        default=PrivacyChoices.PUBLIC
    )
    # Privacidad granular por dominio (Fase 2 / Privacy Core)
    reading_privacy_level = models.CharField(
        max_length=10,
        choices=PrivacyChoices.choices,
        default=PrivacyChoices.PUBLIC,
        db_index=True,
        help_text="Nivel de privacidad específico para la biblioteca y lecturas.",
    )
    activity_privacy_level = models.CharField(
        max_length=10,
        choices=PrivacyChoices.choices,
        default=PrivacyChoices.PUBLIC,
        db_index=True,
        help_text="Nivel de privacidad específico para el feed de actividad y eventos sociales.",
    )
    allow_messages_from = models.CharField(
        max_length=10,
        choices=MessagePrivacyChoices.choices,
        default=MessagePrivacyChoices.FOLLOWED,
        db_index=True,
        help_text="Control de recepción de mensajes directos.",
    )
    # Preferencias de visibilidad por campo (solo aplican cuando el perfil es público)
    show_email = models.BooleanField(default=False)
    show_birth_date = models.BooleanField(default=False)
    show_location = models.BooleanField(default=True)
    show_bio = models.BooleanField(default=True)
    gamification_enabled = models.BooleanField(
        default=True,
        help_text="Permite activar o desactivar opcionalmente la gamificación (retos, rachas, objetivos e insignias).",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Fecha de eliminación y anonimización de la cuenta por solicitud del usuario (Fase 17 - RGPD).",
    )
    terms_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de consentimiento y aceptación de los Términos de Servicio.",
    )
    privacy_accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de consentimiento y aceptación de la Política de Privacidad.",
    )
    onboarding_completed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si el usuario ha completado o desestimado el flujo de bienvenida/onboarding (Fase 19).",
    )
    favorite_categories = models.ManyToManyField(
        'books.Category',
        related_name='favorited_by_users',
        blank=True,
        help_text="Categorías o géneros literarios favoritos seleccionados por el lector durante el onboarding.",
    )

    class Meta:
        ordering = ['-date_joined']

    @property
    def is_moderator(self) -> bool:
        """Determina si el usuario tiene privilegios de moderación o administración."""
        return self.role in (UserRole.MODERATOR, UserRole.ADMIN) or self.is_staff or self.is_superuser

    @property
    def is_author(self) -> bool:
        """Determina si el usuario está registrado o configurado con modalidad de escritor/autor."""
        return self.account_type in (AccountType.AUTHOR, AccountType.BOTH)

    @property
    def is_editor_user(self) -> bool:
        """Determina si el usuario tiene privilegios editoriales o superiores."""
        return self.is_editor or self.role in (UserRole.EDITOR, UserRole.MODERATOR, UserRole.ADMIN) or self.is_staff or self.is_superuser

    @property
    def is_disciplinary_muted(self) -> bool:
        """Determina si el usuario está bajo una sanción activa de silenciamiento disciplinario."""
        if not self.muted_until:
            return False
        return self.muted_until > timezone.now()

    def is_muted(self) -> bool:
        """Método auxiliar para comprobar silenciamiento disciplinario activo."""
        return self.is_disciplinary_muted

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
    FOLLOW_ACCEPTED = 'FOLLOW_ACCEPTED', 'Solicitud de seguimiento aceptada'
    MESSAGE = 'MESSAGE', 'Nuevo mensaje'
    REVIEW = 'REVIEW', 'Nueva reseña'
    LIKE = 'LIKE', 'Me gusta en reseña'
    COMMENT = 'COMMENT', 'Comentario'
    REPLY = 'REPLY', 'Respuesta a comentario'
    LIST_FOLLOW = 'LIST_FOLLOW', 'Interacción en lista social'
    RECOMMENDATION = 'RECOMMENDATION', 'Nueva recomendación'
    SYSTEM = 'SYSTEM', 'Sistema'


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, related_name='notification_preferences', on_delete=models.CASCADE)

    # Preferencias In-App
    in_app_follow = models.BooleanField(default=True)
    in_app_follow_accepted = models.BooleanField(default=True)
    in_app_like = models.BooleanField(default=True)
    in_app_comment = models.BooleanField(default=True)
    in_app_reply = models.BooleanField(default=True)
    in_app_list = models.BooleanField(default=True)
    in_app_message = models.BooleanField(default=True)
    in_app_recommendation = models.BooleanField(default=True)

    # Preferencias Email
    email_follow = models.BooleanField(default=False)
    email_follow_accepted = models.BooleanField(default=False)
    email_like = models.BooleanField(default=False)
    email_comment = models.BooleanField(default=True)
    email_reply = models.BooleanField(default=True)
    email_list = models.BooleanField(default=False)
    email_message = models.BooleanField(default=True)
    email_recommendation = models.BooleanField(default=True)

    # Preferencia Push (diseño preparado para PWA / Web Push futuro)
    push_enabled = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Preferencias de notificaciones de {self.user.username}"


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
    REVIEW_LIKED = 'REVIEW_LIKED', 'Le gustó una reseña'
    COMMENT_ADDED = 'COMMENT_ADDED', 'Comentó en una reseña'
    POST_CREATED = 'POST_CREATED', 'Publicó en el muro'


class UserPost(models.Model):
    """Publicación en el muro social del usuario."""
    author = models.ForeignKey(User, related_name='wall_posts_authored', on_delete=models.CASCADE)
    target_user = models.ForeignKey(User, related_name='wall_posts', on_delete=models.CASCADE)
    content = models.TextField(help_text="Contenido de la publicación en el muro (máx 2000 caracteres)")
    book = models.ForeignKey('books.Book', null=True, blank=True, on_delete=models.SET_NULL, related_name='wall_posts')
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['target_user', '-created_at'], name='idx_post_target_created'),
            models.Index(fields=['author', '-created_at'], name='idx_post_author_created'),
        ]

    def __str__(self):
        return f"Post #{self.pk} de @{self.author.username} en muro de @{self.target_user.username}"


class UserPostLike(models.Model):
    post = models.ForeignKey(UserPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_user_post_like'),
        ]
        indexes = [
            models.Index(fields=['post', 'user'], name='idx_post_like_user'),
        ]

    def __str__(self):
        return f"@{self.user.username} liked post #{self.post_id}"


class UserPostComment(models.Model):
    post = models.ForeignKey(UserPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    text = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at'], name='idx_post_comment_created'),
        ]

    def __str__(self):
        return f"Comentario de @{self.user.username} en post #{self.post_id}"


class Activity(models.Model):
    user = models.ForeignKey(User, related_name='activities', on_delete=models.CASCADE)
    type = models.CharField(max_length=30, choices=ActivityType.choices, db_index=True)
    book = models.ForeignKey('books.Book', null=True, blank=True, on_delete=models.CASCADE, related_name='activities')
    review = models.ForeignKey('books.Review', null=True, blank=True, on_delete=models.CASCADE, related_name='activities')
    post = models.ForeignKey(UserPost, null=True, blank=True, on_delete=models.CASCADE, related_name='activities')
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


class HiddenActivity(models.Model):
    """Permite al usuario ocultar publicaciones específicas de su feed personal (Fase 22)."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hidden_feed_activities')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='hidden_by_users')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'activity')
        indexes = [
            models.Index(fields=['user', 'activity'], name='idx_hidden_user_activity'),
        ]

    def __str__(self):
        return f"HiddenActivity #{self.activity_id} por {self.user.username}"


class ReportStatus(models.TextChoices):
    OPEN = 'OPEN', 'Abierto'
    UNDER_REVIEW = 'UNDER_REVIEW', 'En revisión'
    INVESTIGATING = 'INVESTIGATING', 'En investigación'
    RESOLVED = 'RESOLVED', 'Resuelto'
    REJECTED = 'REJECTED', 'Rechazado'
    DISMISSED = 'DISMISSED', 'Desestimado'

    @classmethod
    def normalize(cls, val: str) -> str:
        """Normaliza aliases canónicos de estado (Roadmap 21.3)."""
        if not val:
            return cls.OPEN
        norm = str(val).upper().strip()
        mapping = {
            'OPEN': cls.OPEN,
            'UNDER_REVIEW': cls.UNDER_REVIEW,
            'INVESTIGATING': cls.UNDER_REVIEW,
            'RESOLVED': cls.RESOLVED,
            'REJECTED': cls.REJECTED,
            'DISMISSED': cls.REJECTED,
        }
        return mapping.get(norm, norm)


class ReportReason(models.TextChoices):
    SPAM = 'SPAM', 'Spam o publicidad no deseada'
    HARASSMENT = 'HARASSMENT', 'Acoso o intimidación'
    HATE_SPEECH = 'HATE_SPEECH', 'Incitación al odio o violencia'
    INAPPROPRIATE = 'INAPPROPRIATE', 'Contenido explícito o inapropiado'
    SPOILER = 'SPOILER', 'Spoilers sin advertencia'
    COPYRIGHT = 'COPYRIGHT', 'Infracción de derechos de autor'
    ILLEGAL_CONTENT = 'ILLEGAL_CONTENT', 'Contenido ilegal o perjudicial'
    IMPERSONATION = 'IMPERSONATION', 'Suplantación de identidad o engaño'
    OTHER = 'OTHER', 'Otro motivo'


class Report(models.Model):
    """
    Modelo de denuncias y moderación de contenido (Fases 16 y 29).
    Permite registrar denuncias de usuarios sobre:
    - Cuentas de usuario (User)
    - Reseñas (Review)
    - Comentarios en reseñas (ReviewComment)
    - Mensajes de chat (Message)
    - Listas de lectura (ReadingList)
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
    USER_MUTE = 'USER_MUTE', 'Silenciamiento Social entre Usuarios'
    USER_UNMUTE = 'USER_UNMUTE', 'Des-silenciamiento Social entre Usuarios'
    MODERATOR_MUTE = 'MODERATOR_MUTE', 'Silenciamiento Disciplinario de Usuario'
    MODERATOR_UNMUTE = 'MODERATOR_UNMUTE', 'Levantamiento de Silenciamiento Disciplinario'
    MODERATION_RESOLVE = 'MODERATION_RESOLVE', 'Resolución de Denuncia'
    MODERATION_REJECT = 'MODERATION_REJECT', 'Rechazo de Denuncia'
    CONTENT_HIDE = 'CONTENT_HIDE', 'Ocultación de Contenido'
    CONTENT_RESTORE = 'CONTENT_RESTORE', 'Restauración de Contenido'
    CONTENT_DELETE = 'CONTENT_DELETE', 'Eliminación de Contenido'
    SECURITY_PASSWORD_CHANGE = 'SECURITY_PASSWORD_CHANGE', 'Cambio de Contraseña'
    USER_DELETE = 'USER_DELETE', 'Eliminación y Anonimización de Cuenta'
    EMAIL_CHANGE = 'EMAIL_CHANGE', 'Cambio de Dirección de Correo Electrónico'
    DATA_EXPORT = 'DATA_EXPORT', 'Exportación de Datos Personales (GDPR)'
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


# ==============================================================================
# Base de Suscripción Premium y Mecenazgo (Fase 31 — RoadmapV2)
# ==============================================================================

class SubscriptionTier(models.TextChoices):
    FREE = 'free', 'Gratuito'
    PREMIUM = 'premium', 'Premium / Mecenas'


class UserSubscription(models.Model):
    """
    Suscripción de usuario para soporte de mecenazgo y funciones premium avanzadas (Fase 31).
    Garantiza que el núcleo de la red social sea 100% gratuito.
    """
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='subscription',
        verbose_name='Usuario',
    )
    tier = models.CharField(
        max_length=20,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
        db_index=True,
        verbose_name='Nivel de suscripción',
    )
    is_active = models.BooleanField(default=True, verbose_name='Activa')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de inicio')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de vencimiento')

    class Meta:
        verbose_name = 'Suscripción de Usuario'
        verbose_name_plural = 'Suscripciones de Usuarios'

    def __str__(self) -> str:
        return f"{self.user.username} - Tier: {self.tier} ({'Activo' if self.is_active else 'Inactivo'})"


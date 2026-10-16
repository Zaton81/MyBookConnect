import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AuthorProfile(models.Model):
    """
    Perfil oficial de un autor en la plataforma, vinculado a su cuenta de usuario
    y opcionalmente enlazado con la entidad Author del catálogo de libros.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='author_profile',
        verbose_name='Cuenta de usuario',
    )
    author = models.ForeignKey(
        'books.Author',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='profiles',
        verbose_name='Autor del catálogo',
        help_text='Registro del catálogo de autores reclamado y verificado',
    )
    pen_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Nombre de pluma / artístico',
    )
    bio = models.TextField(blank=True, verbose_name='Biografía profesional')
    website = models.URLField(blank=True, verbose_name='Sitio web oficial')
    twitter = models.CharField(max_length=100, blank=True, verbose_name='Usuario de Twitter/X')
    instagram = models.CharField(max_length=100, blank=True, verbose_name='Usuario de Instagram')
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Autor verificado',
    )
    verification_notes = models.TextField(
        blank=True,
        verbose_name='Notas de verificación o pruebas de autoría',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authorprofile'
        verbose_name = 'Perfil de Autor'
        verbose_name_plural = 'Perfiles de Autores'

    def __str__(self) -> str:
        name = self.pen_name or (self.author.name if self.author else self.user.username)
        return f"Perfil de Autor: {name} ({'Verificado' if self.is_verified else 'Pendiente'})"


class AuthorAnnouncement(models.Model):
    """
    Publicación oficial, comunicado o adelanto literario publicado por un autor para sus lectores.
    """
    class PublicationType(models.TextChoices):
        ANNOUNCEMENT = 'ANNOUNCEMENT', 'Comunicado oficial'
        CHAPTER_PREVIEW = 'CHAPTER_PREVIEW', 'Adelanto de capítulo'
        AUTHOR_DIARY = 'AUTHOR_DIARY', 'Diario de escritura'
        DELETED_SCENE = 'DELETED_SCENE', 'Escena eliminada / Extra'
        Q_AND_A = 'Q_AND_A', 'Preguntas y Respuestas'

    author_profile = models.ForeignKey(
        AuthorProfile,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name='Perfil de autor',
    )
    author = models.ForeignKey(
        'books.Author',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name='Autor del catálogo',
    )
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='author_announcements',
        verbose_name='Libro relacionado',
    )
    title = models.CharField(max_length=200, verbose_name='Título de la publicación')
    content = models.TextField(verbose_name='Contenido completo')
    excerpt = models.CharField(max_length=500, blank=True, verbose_name='Extracto / Resumen previo')
    publication_type = models.CharField(
        max_length=30,
        choices=PublicationType.choices,
        default=PublicationType.ANNOUNCEMENT,
        verbose_name='Tipo de publicación',
    )
    has_spoilers = models.BooleanField(default=False, verbose_name='Contiene spoilers')
    spoiler_warning = models.CharField(max_length=255, blank=True, verbose_name='Aviso de spoiler')
    estimated_reading_time = models.PositiveIntegerField(default=1, verbose_name='Minutos estimados de lectura')
    is_pinned = models.BooleanField(default=False, verbose_name='Fijado en el perfil')
    is_draft = models.BooleanField(default=False, db_index=True, verbose_name='Es borrador')
    is_paid = models.BooleanField(default=False, db_index=True, verbose_name='Publicación de pago')
    price = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Precio de acceso')
    is_moderated = models.BooleanField(default=False, db_index=True, verbose_name='Censurado / Ocultado por moderación')
    moderation_reason = models.CharField(max_length=255, blank=True, verbose_name='Motivo de moderación')
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='moderated_author_announcements',
        verbose_name='Moderado por',
    )
    moderated_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de moderación')
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Fecha de publicación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authorannouncement'
        verbose_name = 'Publicación de Autor'
        verbose_name_plural = 'Publicaciones de Autores'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self) -> str:
        author_name = self.author.name if self.author else (self.author_profile.pen_name or self.author_profile.user.username)
        return f"[{self.get_publication_type_display()}] {author_name} - {self.title}"

    def save(self, *args, **kwargs):
        if not self.excerpt and self.content:
            clean_text = self.content.strip().replace('\n', ' ')
            self.excerpt = clean_text[:280] + ('...' if len(clean_text) > 280 else '')
        if not self.estimated_reading_time and self.content:
            words = len(self.content.split())
            self.estimated_reading_time = max(1, round(words / 200))
        if not self.author and self.author_profile and self.author_profile.author:
            self.author = self.author_profile.author
        super().save(*args, **kwargs)


class AuthorEvent(models.Model):
    """
    Evento literario organizado por o en torno a un autor (presentaciones, firmas, Q&A, lecturas, talleres).
    """
    class EventType(models.TextChoices):
        BOOK_LAUNCH = 'BOOK_LAUNCH', 'Lanzamiento / Presentación'
        SIGNING = 'SIGNING', 'Firma de ejemplares'
        QA_SESSION = 'QA_SESSION', 'Sesión de preguntas (Q&A)'
        READING = 'READING', 'Lectura pública'
        WORKSHOP = 'WORKSHOP', 'Taller literario'
        OTHER = 'OTHER', 'Otro evento'

    class EventFormat(models.TextChoices):
        ONLINE = 'ONLINE', 'Virtual / En línea'
        IN_PERSON = 'IN_PERSON', 'Presencial'
        HYBRID = 'HYBRID', 'Híbrido'

    author = models.ForeignKey(
        'books.Author',
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name='Autor',
    )
    author_profile = models.ForeignKey(
        AuthorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name='Perfil oficial del autor',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_author_events',
        verbose_name='Creado por',
    )
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='author_events',
        verbose_name='Libro relacionado',
    )
    title = models.CharField(max_length=255, verbose_name='Título del evento')
    description = models.TextField(verbose_name='Descripción del evento')
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        default=EventType.BOOK_LAUNCH,
        verbose_name='Tipo de evento',
    )
    event_format = models.CharField(
        max_length=20,
        choices=EventFormat.choices,
        default=EventFormat.ONLINE,
        verbose_name='Formato',
    )
    start_time = models.DateTimeField(db_index=True, verbose_name='Fecha y hora de inicio')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Fecha y hora de fin')
    event_timezone = models.CharField(max_length=50, default='Europe/Madrid', verbose_name='Zona horaria')
    location_name = models.CharField(max_length=255, blank=True, verbose_name='Lugar o plataforma (ej. Librería Alberti / Zoom)')
    location_address = models.CharField(max_length=255, blank=True, verbose_name='Dirección física')
    online_url = models.URLField(max_length=500, blank=True, verbose_name='Enlace virtual o streaming')
    max_attendees = models.PositiveIntegerField(null=True, blank=True, verbose_name='Aforo máximo')
    is_cancelled = models.BooleanField(default=False, verbose_name='Cancelado')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authorevent'
        verbose_name = 'Evento de Autor'
        verbose_name_plural = 'Eventos de Autores'
        ordering = ['start_time']

    def __str__(self) -> str:
        return f"[{self.get_event_type_display()}] {self.title} - {self.author.name}"

    @property
    def registered_count(self) -> int:
        return self.attendees.filter(status=AuthorEventAttendee.AttendeeStatus.REGISTERED).count()

    @property
    def waitlist_count(self) -> int:
        return self.attendees.filter(status=AuthorEventAttendee.AttendeeStatus.WAITLIST).count()

    @property
    def is_full(self) -> bool:
        if not self.max_attendees:
            return False
        return self.registered_count >= self.max_attendees


class AuthorEventAttendee(models.Model):
    """
    Inscripción de un lector en un evento de autor, con soporte de lista de espera y preguntas para el autor.
    """
    class AttendeeStatus(models.TextChoices):
        REGISTERED = 'REGISTERED', 'Inscrito'
        WAITLIST = 'WAITLIST', 'Lista de espera'
        CANCELLED = 'CANCELLED', 'Cancelado'

    event = models.ForeignKey(
        AuthorEvent,
        on_delete=models.CASCADE,
        related_name='attendees',
        verbose_name='Evento',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='author_event_attendances',
        verbose_name='Usuario asistente',
    )
    status = models.CharField(
        max_length=20,
        choices=AttendeeStatus.choices,
        default=AttendeeStatus.REGISTERED,
        db_index=True,
        verbose_name='Estado de inscripción',
    )
    notes = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Pregunta para el autor o nota adicional',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de registro')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authoreventattendee'
        verbose_name = 'Asistente a Evento'
        verbose_name_plural = 'Asistentes a Eventos'
        constraints = [
            models.UniqueConstraint(fields=['event', 'user'], name='unique_event_user_attendance'),
        ]
        ordering = ['created_at']

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.event.title} ({self.get_status_display()})"


class AuthorNewsletter(models.Model):
    """
    Boletín periódico o canal de novedades de un autor literario.
    """
    class Frequency(models.TextChoices):
        WEEKLY = 'WEEKLY', 'Semanal'
        BIWEEKLY = 'BIWEEKLY', 'Quincenal'
        MONTHLY = 'MONTHLY', 'Mensual'
        OCCASIONAL = 'OCCASIONAL', 'Ocasional'

    author = models.ForeignKey(
        'books.Author',
        on_delete=models.CASCADE,
        related_name='newsletters',
        verbose_name='Autor del catálogo',
    )
    author_profile = models.ForeignKey(
        AuthorProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='newsletters',
        verbose_name='Perfil oficial del autor',
    )
    title = models.CharField(max_length=255, verbose_name='Título del boletín')
    description = models.TextField(blank=True, verbose_name='Descripción del boletín')
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.MONTHLY,
        verbose_name='Frecuencia estimada',
    )
    is_active = models.BooleanField(default=True, verbose_name='Boletín activo')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authornewsletter'
        verbose_name = 'Boletín de Autor'
        verbose_name_plural = 'Boletines de Autores'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Newsletter: {self.title} ({self.author.name})"

    @property
    def active_subscribers_count(self) -> int:
        return self.subscribers.filter(is_active=True).count()

    @property
    def sent_issues_count(self) -> int:
        return self.issues.filter(status=AuthorNewsletterIssue.IssueStatus.SENT).count()


class AuthorNewsletterSubscriber(models.Model):
    """
    Suscripción de un lector al boletín de un autor, con token seguro para baja inmediata.
    """
    newsletter = models.ForeignKey(
        AuthorNewsletter,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Boletín',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='author_newsletter_subscriptions',
        verbose_name='Lector suscriptor',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Suscripción activa')
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, verbose_name='Token de cancelación')
    subscribed_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de suscripción')
    unsubscribed_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de baja')

    class Meta:
        db_table = 'books_authornewslettersubscriber'
        verbose_name = 'Suscriptor de Boletín'
        verbose_name_plural = 'Suscriptores de Boletines'
        constraints = [
            models.UniqueConstraint(fields=['newsletter', 'user'], name='unique_newsletter_user_subscription'),
        ]
        ordering = ['-subscribed_at']

    def __str__(self) -> str:
        status_label = "Activo" if self.is_active else "Baja"
        return f"{self.user.username} -> {self.newsletter.title} ({status_label})"


class AuthorNewsletterIssue(models.Model):
    """
    Entrega o edición específica del boletín de un autor (borrador, programada o enviada).
    """
    class IssueStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Borrador'
        SCHEDULED = 'SCHEDULED', 'Programado'
        SENT = 'SENT', 'Enviado'

    newsletter = models.ForeignKey(
        AuthorNewsletter,
        on_delete=models.CASCADE,
        related_name='issues',
        verbose_name='Boletín',
    )
    title = models.CharField(max_length=255, verbose_name='Título de la entrega')
    subject = models.CharField(max_length=255, verbose_name='Asunto / Cabecera')
    content = models.TextField(verbose_name='Contenido del boletín')
    status = models.CharField(
        max_length=20,
        choices=IssueStatus.choices,
        default=IssueStatus.DRAFT,
        db_index=True,
        verbose_name='Estado',
    )
    scheduled_for = models.DateTimeField(null=True, blank=True, verbose_name='Fecha programada')
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Fecha de envío')
    recipients_count = models.PositiveIntegerField(default=0, verbose_name='Destinatarios alcanzados')
    views_count = models.PositiveIntegerField(default=0, verbose_name='Aperturas registradas')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authornewsletterissue'
        verbose_name = 'Entrega de Boletín'
        verbose_name_plural = 'Entregas de Boletines'
        ordering = ['-sent_at', '-created_at']

    def __str__(self) -> str:
        return f"[{self.get_status_display()}] {self.newsletter.title} - {self.title}"


class AuthorClaimStatus(models.TextChoices):
    PENDING = 'pending', 'Pendiente'
    APPROVED = 'approved', 'Aprobada'
    REJECTED = 'rejected', 'Rechazada'
    CANCELLED = 'cancelled', 'Cancelada'


class AuthorClaim(models.Model):
    """
    Solicitud formal de un usuario registrado para reclamar la autoría y página de un autor.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='author_claims',
        verbose_name='Usuario solicitante',
    )
    author = models.ForeignKey(
        'books.Author',
        on_delete=models.CASCADE,
        related_name='claims',
        verbose_name='Autor del catálogo',
    )
    status = models.CharField(
        max_length=20,
        choices=AuthorClaimStatus.choices,
        default=AuthorClaimStatus.PENDING,
        db_index=True,
        verbose_name='Estado de la solicitud',
    )
    proof_description = models.TextField(
        verbose_name='Descripción de autoría o acreditación de identidad',
        help_text='Indica cómo contrastar tu autoría (web oficial, editorial, ISBN, etc.)',
    )
    contact_email = models.EmailField(
        verbose_name='Email de contacto profesional',
        blank=True,
        null=True,
    )
    supporting_link = models.URLField(
        blank=True,
        null=True,
        verbose_name='Enlace de respaldo oficial',
    )
    moderation_notes = models.TextField(
        blank=True,
        verbose_name='Notas de moderación interna',
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='moderated_author_claims',
        verbose_name='Moderador asignado',
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Fecha de solicitud')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        db_table = 'books_authorclaim'
        verbose_name = 'Reclamación de Autor'
        verbose_name_plural = 'Reclamaciones de Autores'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Reclamación: {self.user.username} -> {self.author.name} [{self.status}]"

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class ReadingClub(models.Model):
    """
    Club de lectura para grupos literarios y lecturas conjuntas.
    RoadmapV3 Sección 30.1.
    """
    name = models.CharField(max_length=200, verbose_name='Nombre del club')
    slug = models.SlugField(max_length=220, unique=True, blank=True, verbose_name='Slug URL')
    description = models.TextField(blank=True, verbose_name='Descripción')
    cover_image = models.ImageField(upload_to='club_covers/', null=True, blank=True, verbose_name='Imagen de portada')
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_clubs',
        verbose_name='Creador',
    )
    is_private = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='Club privado (requiere aprobación)',
    )
    rules = models.TextField(blank=True, verbose_name='Reglas de convivencia')
    current_book = models.ForeignKey(
        'books.Book',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='active_in_clubs',
        verbose_name='Lectura actual',
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Club de Lectura'
        verbose_name_plural = 'Clubs de Lectura'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'club'
            slug = base_slug
            counter = 1
            while ReadingClub.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    @property
    def members_count(self) -> int:
        return self.memberships.filter(status=ReadingClubMember.Status.ACTIVE).count()


class ReadingClubMember(models.Model):
    """
    Membresía y roles dentro de un club de lectura.
    """
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        MODERATOR = 'MODERATOR', 'Moderador'
        MEMBER = 'MEMBER', 'Miembro'

    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Activo'
        PENDING = 'PENDING', 'Pendiente de aprobación'
        BANNED = 'BANNED', 'Bloqueado'

    club = models.ForeignKey(
        ReadingClub,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Club de lectura',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_memberships',
        verbose_name='Usuario miembro',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        verbose_name='Rol en el club',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        verbose_name='Estado de membresía',
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de ingreso')

    class Meta:
        verbose_name = 'Miembro de Club'
        verbose_name_plural = 'Miembros de Clubs'
        unique_together = ('club', 'user')
        ordering = ['-joined_at']

    def __str__(self) -> str:
        return f"{self.user.username} en {self.club.name} ({self.role} - {self.status})"


class ReadingClubBook(models.Model):
    """
    Plan de lecturas conjuntas (actuales, pasadas y agendadas) de un club.
    """
    class ReadingStatus(models.TextChoices):
        CURRENT = 'CURRENT', 'Lectura Actual'
        UPCOMING = 'UPCOMING', 'Próxima Lectura'
        FINISHED = 'FINISHED', 'Lectura Finalizada'

    club = models.ForeignKey(
        ReadingClub,
        on_delete=models.CASCADE,
        related_name='reading_plan',
        verbose_name='Club',
    )
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='club_readings',
        verbose_name='Libro',
    )
    status = models.CharField(
        max_length=20,
        choices=ReadingStatus.choices,
        default=ReadingStatus.UPCOMING,
        db_index=True,
        verbose_name='Estado de lectura',
    )
    start_date = models.DateField(null=True, blank=True, verbose_name='Fecha de inicio')
    end_date = models.DateField(null=True, blank=True, verbose_name='Fecha estimada de fin')
    target_milestones = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Hitos o metas de capítulos (ej. Capítulos 1 al 10 para semana 1)',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Añadido el')

    class Meta:
        verbose_name = 'Lectura de Club'
        verbose_name_plural = 'Lecturas de Clubs'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.book.title} en {self.club.name} [{self.status}]"


class ReadingClubDiscussion(models.Model):
    """
    Hilo de debate temático dentro de un club de lectura con soporte de advertencia de spoilers.
    """
    club = models.ForeignKey(
        ReadingClub,
        on_delete=models.CASCADE,
        related_name='discussions',
        verbose_name='Club',
    )
    book = models.ForeignKey(
        'books.Book',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='club_discussions',
        verbose_name='Libro vinculado',
    )
    title = models.CharField(max_length=255, verbose_name='Título del debate')
    content = models.TextField(verbose_name='Contenido o pregunta inicial')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_discussions',
        verbose_name='Autor del debate',
    )
    is_pinned = models.BooleanField(default=False, db_index=True, verbose_name='Fijado en la parte superior')
    has_spoilers = models.BooleanField(default=False, verbose_name='Contiene spoilers')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Debate de Club'
        verbose_name_plural = 'Debates de Clubs'
        ordering = ['-is_pinned', '-created_at']

    def __str__(self) -> str:
        return f"Debate: {self.title} ({self.club.name})"

    @property
    def comments_count(self) -> int:
        if hasattr(self, '_annotated_comments_count'):
            return self._annotated_comments_count
        return self.comments.count()


class ReadingClubDiscussionComment(models.Model):
    """
    Comentario en un hilo de debate de club de lectura.
    """
    discussion = models.ForeignKey(
        ReadingClubDiscussion,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Debate',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='club_discussion_comments',
        verbose_name='Autor del comentario',
    )
    content = models.TextField(verbose_name='Comentario')
    has_spoilers = models.BooleanField(default=False, verbose_name='Contiene spoilers')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de publicación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Comentario de Debate'
        verbose_name_plural = 'Comentarios de Debates'
        ordering = ['created_at']

    def __str__(self) -> str:
        return f"Comentario de {self.author.username} en {self.discussion.title}"

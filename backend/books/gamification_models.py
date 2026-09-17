from django.conf import settings
from django.db import models
from django.utils import timezone


class ReadingGoal(models.Model):
    """
    Objetivo anual de lectura fijado por el usuario (Fase 54).
    Ejemplo: 'Leer 20 libros en 2026'.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_goals',
    )
    year = models.PositiveIntegerField(db_index=True)
    target_books = models.PositiveIntegerField(default=12)
    target_pages = models.PositiveIntegerField(default=0, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'year')
        ordering = ['-year']
        verbose_name = 'Objetivo de lectura'
        verbose_name_plural = 'Objetivos de lectura'

    def __str__(self):
        return f"{self.user.username} - Meta {self.year}: {self.target_books} libros"


class ReadingStreak(models.Model):
    """
    Métricas de racha de lectura consecutiva del usuario (Fase 54).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reading_streak',
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_reading_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Racha de lectura'
        verbose_name_plural = 'Rachas de lectura'

    def __str__(self):
        return f"{self.user.username}: {self.current_streak} días (récord: {self.longest_streak})"


class DailyReadingLog(models.Model):
    """
    Registro diario de sesión de lectura para alimentar la racha y estadísticas (Fase 54).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='daily_reading_logs',
    )
    date = models.DateField(default=timezone.now, db_index=True)
    pages_read = models.PositiveIntegerField(default=0)
    minutes_read = models.PositiveIntegerField(default=0)
    books = models.ManyToManyField(
        'books.Book',
        blank=True,
        related_name='daily_logs',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        verbose_name = 'Log diario de lectura'
        verbose_name_plural = 'Logs diarios de lectura'

    def __str__(self):
        return f"{self.user.username} - {self.date}: {self.pages_read} págs / {self.minutes_read} min"


class BadgeCategory(models.TextChoices):
    READING = 'reading', 'Lectura'
    STREAK = 'streak', 'Rachas'
    REVIEWS = 'reviews', 'Reseñas'
    COMMUNITY = 'community', 'Comunidad'
    CHALLENGES = 'challenges', 'Retos'


class Badge(models.Model):
    """
    Catálogo de insignias y logros desbloqueables (Fase 54).
    """
    slug = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='📚')
    category = models.CharField(
        max_length=50,
        choices=BadgeCategory.choices,
        default=BadgeCategory.READING,
        db_index=True,
    )
    points = models.PositiveIntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'points', 'name']
        verbose_name = 'Insignia'
        verbose_name_plural = 'Insignias'

    def __str__(self):
        return f"{self.icon} {self.name} ({self.get_category_display()})"


class UserBadge(models.Model):
    """
    Insignias otorgadas a un usuario particular (Fase 54).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='badges',
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='user_awards',
    )
    awarded_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('user', 'badge')
        ordering = ['-awarded_at']
        verbose_name = 'Insignia de usuario'
        verbose_name_plural = 'Insignias de usuarios'

    def __str__(self):
        return f"{self.user.username} obtuvo {self.badge.name} ({self.awarded_at.date()})"


class ChallengeType(models.TextChoices):
    BOOKS_COUNT = 'books_count', 'Libros leídos'
    PAGES_COUNT = 'pages_count', 'Páginas leídas'
    REVIEWS_COUNT = 'reviews_count', 'Reseñas publicadas'
    GENRE_BOOKS = 'genre_books', 'Libros de género específico'


class ReadingChallenge(models.Model):
    """
    Retos periódicos o temáticos de lectura (mensual, veraniego, etc.) (Fase 54).
    """
    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(
        max_length=30,
        choices=ChallengeType.choices,
        default=ChallengeType.BOOKS_COUNT,
    )
    target_count = models.PositiveIntegerField(default=5)
    category = models.ForeignKey(
        'books.Category',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='challenges',
        help_text="Categoría requerida si el reto es de tipo género específico",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    badge_reward = models.ForeignKey(
        Badge,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='challenges',
        help_text="Insignia opcional que se otorga al superar el reto",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-end_date']
        verbose_name = 'Reto de lectura'
        verbose_name_plural = 'Retos de lectura'

    def __str__(self):
        return f"{self.title} ({self.start_date} a {self.end_date})"


class UserChallenge(models.Model):
    """
    Participación y progreso del usuario en un reto (Fase 54).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='challenges',
    )
    challenge = models.ForeignKey(
        ReadingChallenge,
        on_delete=models.CASCADE,
        related_name='participants',
    )
    current_progress = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'challenge')
        ordering = ['-joined_at']
        verbose_name = 'Participación en reto'
        verbose_name_plural = 'Participaciones en retos'

    def __str__(self):
        status_str = "Completado" if self.is_completed else f"{self.current_progress}/{self.challenge.target_count}"
        return f"{self.user.username} en '{self.challenge.title}': {status_str}"

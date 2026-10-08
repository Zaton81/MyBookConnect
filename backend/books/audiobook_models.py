import math
from django.conf import settings
from django.db import models
from django.utils import timezone


class AudiobookTrack(models.Model):
    """
    Pista de audio o capítulo perteneciente a un audiolibro.
    RoadmapV3 Sección 30 — Sprint 18: Audiolibros & TTS.
    """
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='audio_tracks',
        verbose_name='Libro asociado',
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Título de la pista / Capítulo',
    )
    track_number = models.PositiveIntegerField(
        default=1,
        verbose_name='Número de pista',
    )
    audio_file = models.FileField(
        upload_to='audiobooks/',
        null=True,
        blank=True,
        verbose_name='Archivo de audio',
    )
    audio_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='URL externa o CDN del audio',
    )
    duration_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name='Duración en segundos',
    )
    narrator_name = models.CharField(
        max_length=150,
        blank=True,
        default='',
        verbose_name='Nombre del narrador/a',
    )
    is_sample = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='¿Es muestra gratuita / preview pública?',
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de subida',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última modificación',
    )

    class Meta:
        verbose_name = 'Pista de Audiolibro'
        verbose_name_plural = 'Pistas de Audiolibros'
        ordering = ['book', 'track_number']
        indexes = [
            models.Index(fields=['book', 'track_number'], name='idx_audio_book_track'),
            models.Index(fields=['is_sample'], name='idx_audio_is_sample'),
        ]

    def __str__(self) -> str:
        return f"{self.book.title} - #{self.track_number} {self.title}"

    @property
    def stream_url(self) -> str:
        """Devuelve la URL accesible de la pista (archivo local o CDN)."""
        if self.audio_file:
            return self.audio_file.url
        return self.audio_url or ''

    @property
    def formatted_duration(self) -> str:
        """Devuelve la duración formateada mm:ss o hh:mm:ss."""
        total = self.duration_seconds
        hours = total // 3600
        minutes = (total % 3600) // 60
        seconds = total % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"


class UserAudiobookProgress(models.Model):
    """
    Progreso de escucha, marcapáginas y preferencias de reproducción del usuario.
    RoadmapV3 Sección 30 — Sprint 18: Audiolibros & TTS.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='audiobook_progress',
        verbose_name='Usuario',
    )
    book = models.ForeignKey(
        'books.Book',
        on_delete=models.CASCADE,
        related_name='audiobook_user_progress',
        verbose_name='Libro',
    )
    current_track = models.ForeignKey(
        AudiobookTrack,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='user_progress',
        verbose_name='Pista actual',
    )
    position_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name='Posición actual de escucha en segundos',
    )
    playback_speed = models.FloatField(
        default=1.0,
        verbose_name='Velocidad de reproducción preferida',
    )
    is_completed = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='¿Audiolibro completado?',
    )
    last_listened_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name='Última sesión de escucha',
    )

    class Meta:
        verbose_name = 'Progreso de Audiolibro'
        verbose_name_plural = 'Progresos de Audiolibros'
        unique_together = [('user', 'book')]
        ordering = ['-last_listened_at']
        indexes = [
            models.Index(fields=['user', '-last_listened_at'], name='idx_audio_user_last_listen'),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} en {self.book.title} ({self.position_seconds}s)"

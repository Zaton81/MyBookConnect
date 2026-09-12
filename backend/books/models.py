import re

from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify

from mybookconnect.media_security import validate_author_photo, validate_cover_image


def normalize_isbn(value: str | None) -> str | None:
    """Normaliza un ISBN eliminando guiones, espacios y convirtiendo a mayúsculas."""
    if not value:
        return None
    cleaned = re.sub(r'[^0-9X]', '', str(value).upper().strip())
    return cleaned if cleaned else None


class Author(models.Model):
    name = models.CharField(max_length=200)
    biography = models.TextField(blank=True, null=True)
    photo = models.ImageField(
        upload_to='author_photos/',
        null=True,
        blank=True,
        validators=[validate_author_photo],
        help_text="Fotografía del autor (JPEG, PNG, WebP; máx 5MB; dimensiones 50x50 a 6000x6000px)",
    )
    enrichment_attempted = models.BooleanField(default=False)

    class Meta:
        indexes = [
            GinIndex(fields=['name'], name='idx_author_name_trgm', opclasses=['gin_trgm_ops']),
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=300)
    author = models.ForeignKey(Author, null=True, blank=True, on_delete=models.SET_NULL, related_name='books')
    isbn = models.CharField(max_length=30, blank=True, null=True, db_index=True)
    google_volume_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    openlibrary_work_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    openlibrary_edition_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    cover = models.ImageField(
        upload_to='covers/',
        null=True,
        blank=True,
        validators=[validate_cover_image],
        help_text="Portada del libro (JPEG, PNG, WebP; máx 10MB; dimensiones 50x50 a 6000x6000px)",
    )
    description = models.TextField(blank=True, null=True)
    published_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    average_rating = models.FloatField(null=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='books', blank=True)
    enrichment_attempted = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title'], name='idx_book_title'),
            models.Index(fields=['title', 'author'], name='idx_book_title_author'),
            models.Index(fields=['-created_at'], name='idx_book_created_at'),
            GinIndex(fields=['title'], name='idx_book_title_trgm', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['description'], name='idx_book_desc_trgm', opclasses=['gin_trgm_ops']),
        ]

    def save(self, *args, **kwargs):
        if self.isbn:
            self.isbn = normalize_isbn(self.isbn)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title}"


class ReadingStatus(models.TextChoices):
    WANT_TO_READ = 'want_to_read', 'Quiero leer'
    READING = 'reading', 'Leyendo'
    READ = 'read', 'Leído'
    ABANDONED = 'abandoned', 'Abandonado'


class UserBook(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_books')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='user_entries')
    status = models.CharField(
        max_length=20,
        choices=ReadingStatus.choices,
        default=ReadingStatus.WANT_TO_READ,
        db_index=True,
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje de lectura de 0 a 100",
    )
    current_page = models.PositiveIntegerField(
        default=0,
        help_text="Página actual de lectura",
    )
    started_at = models.DateField(null=True, blank=True)
    finished_at = models.DateField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    is_digital = models.BooleanField(default=False)
    owned = models.BooleanField(default=False)
    wishlist = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'book')
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'book']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'wishlist']),
            models.Index(fields=['is_read', '-updated_at'], name='idx_userbook_read_updated'),
            models.Index(fields=['status', '-updated_at'], name='idx_userbook_status_updated'),
        ]

    def save(self, *args, **kwargs):
        # Sincronización bidireccional entre status e is_read para compatibilidad
        if self.status == ReadingStatus.READ:
            self.is_read = True
            if self.progress < 100:
                self.progress = 100
            if not self.finished_at:
                self.finished_at = timezone.now().date()
        elif self.is_read and self.status == ReadingStatus.WANT_TO_READ:
            self.status = ReadingStatus.READ
            if not self.finished_at:
                self.finished_at = timezone.now().date()
        elif self.status != ReadingStatus.READ:
            self.is_read = False

        if self.status == ReadingStatus.READING and not self.started_at:
            self.started_at = timezone.now().date()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.get_status_display()})"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_review_user_book'),
        ]
        indexes = [
            models.Index(fields=['book', '-created_at'], name='idx_review_book_created'),
            models.Index(fields=['user', '-created_at'], name='idx_review_user_created'),
            models.Index(fields=['-created_at'], name='idx_review_created_at'),
        ]

    def __str__(self):
        return f"Reseña {self.user.username} - {self.book.title}"


class ReviewLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_likes')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'review'], name='unique_review_like_user_review'),
        ]
        indexes = [
            models.Index(fields=['review', '-created_at'], name='idx_rvlike_review_created'),
            models.Index(fields=['user', '-created_at'], name='idx_rvlike_user_created'),
        ]

    def __str__(self):
        return f"{self.user.username} liked Review {self.review_id}"


class ReviewComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_comments')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['review', 'created_at'], name='idx_rvcomment_review_created'),
            models.Index(fields=['review', 'deleted_at'], name='idx_rvcomment_review_del'),
        ]

    def __str__(self):
        return f"Comentario de {self.user.username} en Reseña {self.review_id}"


class ErrataType(models.TextChoices):
    ERRATA = 'errata', 'Errata'
    SUGGESTION = 'suggestion', 'Sugerencia'
    OTHER = 'other', 'Otro'


class ErrataStatus(models.TextChoices):
    OPEN = 'open', 'Abierta'
    APPROVED = 'approved', 'Aprobada'
    REJECTED = 'rejected', 'Rechazada'


class Errata(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='erratas')
    book = models.ForeignKey(Book, null=True, blank=True, on_delete=models.CASCADE, related_name='erratas')
    author = models.ForeignKey(Author, null=True, blank=True, on_delete=models.CASCADE, related_name='erratas')
    type = models.CharField(max_length=20, choices=ErrataType.choices, default=ErrataType.ERRATA)
    text = models.TextField()
    status = models.CharField(max_length=20, choices=ErrataStatus.choices, default=ErrataStatus.OPEN)
    resolution_notes = models.TextField(blank=True, null=True)
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='handled_erratas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='idx_errata_status_created'),
            models.Index(fields=['book', 'status'], name='idx_errata_book_status'),
        ]

    def __str__(self):
        target = self.book.title if self.book else (self.author.name if self.author else 'N/A')
        return f"{self.type} - {target} ({self.status})"


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
@receiver(post_save, sender=UserBook)
@receiver(post_delete, sender=UserBook)
def update_book_rating(sender, instance, **kwargs):
    book = instance.book
    try:
        from .tasks import recalculate_book_rating_task
        recalculate_book_rating_task.delay(book.id)
    except Exception:
        # Fallback síncrono si el broker no está disponible o en tests síncronos
        review_avg = Review.objects.filter(book=book, rating__isnull=False).aggregate(Avg('rating'))['rating__avg']
        if review_avg is not None:
            book.average_rating = round(review_avg, 2)
        else:
            ub_avg = UserBook.objects.filter(book=book, rating__isnull=False).aggregate(Avg('rating'))['rating__avg']
            book.average_rating = round(ub_avg, 2) if ub_avg else None
        book.save(update_fields=['average_rating'])

    try:
        from .cache_utils import invalidate_book_cache
        invalidate_book_cache(book.id)
    except Exception:
        pass


@receiver(post_save, sender=Book)
@receiver(post_delete, sender=Book)
def invalidate_book_cache_signal(sender, instance, **kwargs):
    try:
        from .cache_utils import invalidate_book_cache
        invalidate_book_cache(instance.id)
    except Exception:
        pass


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def handle_review_signals(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    # Invalida caché de estadísticas y recomendaciones
    try:
        from .cache_utils import (
            invalidate_book_recommendations_cache,
            invalidate_user_recommendations_cache,
            invalidate_user_stats_cache,
        )
        invalidate_user_stats_cache(instance.user_id)
        invalidate_user_recommendations_cache(instance.user_id)
        invalidate_book_recommendations_cache(instance.book_id)
    except Exception:
        pass

    if created:
        try:
            from users.activity_service import record_activity
            from users.models import ActivityType

            record_activity(
                user=instance.user,
                activity_type=ActivityType.REVIEW_CREATED,
                book=instance.book,
                review=instance,
                metadata={'rating': instance.rating, 'title': instance.title or ''},
            )
        except Exception:
            pass


@receiver(post_save, sender=UserBook)
@receiver(post_delete, sender=UserBook)
def handle_userbook_signals(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    # Invalida caché de estadísticas y recomendaciones
    try:
        from .cache_utils import (
            invalidate_book_recommendations_cache,
            invalidate_user_recommendations_cache,
            invalidate_user_stats_cache,
        )
        invalidate_user_stats_cache(instance.user_id)
        invalidate_user_recommendations_cache(instance.user_id)
        invalidate_book_recommendations_cache(instance.book_id)
    except Exception:
        pass

    try:
        from users.activity_service import record_activity
        from users.models import ActivityType

        if created:
            record_activity(
                user=instance.user,
                activity_type=ActivityType.BOOK_ADDED,
                book=instance.book,
                metadata={'status': instance.status},
            )
        else:
            if instance.status == ReadingStatus.READ or instance.is_read:
                record_activity(
                    user=instance.user,
                    activity_type=ActivityType.BOOK_FINISHED,
                    book=instance.book,
                    metadata={'rating': instance.rating},
                )
            elif instance.status == ReadingStatus.READING:
                record_activity(
                    user=instance.user,
                    activity_type=ActivityType.BOOK_STARTED,
                    book=instance.book,
                    metadata={'progress': instance.progress},
                )
            elif instance.rating is not None:
                record_activity(
                    user=instance.user,
                    activity_type=ActivityType.BOOK_RATED,
                    book=instance.book,
                    metadata={'rating': instance.rating},
                )
    except Exception:
        pass


class LegalDocument(models.Model):
    DOCUMENT_TYPES = [
        ('terms', 'Términos del Servicio'),
        ('privacy', 'Política de Privacidad'),
        ('cookies', 'Política de Cookies'),
        ('legal_notice', 'Aviso Legal'),
    ]
    slug = models.SlugField(max_length=50, unique=True, choices=DOCUMENT_TYPES)
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Contenido en Markdown o HTML")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_legal_documents'
    )

    def __str__(self):
        return self.title


class ReadingListPrivacy(models.TextChoices):
    PUBLIC = 'public', 'Pública'
    FOLLOWERS = 'followers', 'Solo seguidores'
    PRIVATE = 'private', 'Privada'


class ReadingList(models.Model):
    """
    Lista de lectura personalizada (Fase 21).
    Permite organizar colecciones temáticas (Favoritos, Por leer 2027, etc.)
    con visibilidad configurable y ordenamiento de libros.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_lists')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220)
    description = models.TextField(blank=True, default='')
    privacy = models.CharField(
        max_length=20,
        choices=ReadingListPrivacy.choices,
        default=ReadingListPrivacy.PUBLIC,
        db_index=True,
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'slug'], name='unique_user_reading_list_slug')
        ]
        indexes = [
            models.Index(fields=['user', '-updated_at'], name='idx_readinglist_user_updated'),
            models.Index(fields=['privacy', '-updated_at'], name='idx_readinglist_priv_updated'),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'lista'
            slug = base_slug
            counter = 1
            while ReadingList.objects.filter(user=self.user, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class ReadingListItem(models.Model):
    """
    Elemento individual dentro de una lista de lectura con posición y notas opcionales.
    """
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name='items')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reading_list_items')
    position = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True, default='')
    added_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['position', 'added_at']
        constraints = [
            models.UniqueConstraint(fields=['reading_list', 'book'], name='unique_reading_list_book')
        ]
        indexes = [
            models.Index(fields=['reading_list', 'position'], name='idx_readinglistitem_pos'),
        ]

    def __str__(self):
        return f"{self.reading_list.name} - {self.book.title} (#{self.position})"


class ReadingListFollow(models.Model):
    """
    Seguimiento de listas de lectura públicas por parte de otros usuarios.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_reading_lists')
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'reading_list'], name='unique_reading_list_follow')
        ]
        indexes = [
            models.Index(fields=['user', '-created_at'], name='idx_readinglistfollow_user'),
        ]

    def __str__(self):
        return f"{self.user.username} sigue {self.reading_list.name}"


class RecommendationFeedbackAction(models.TextChoices):
    RECOMMENDATION_SHOWN = 'recommendation_shown', 'Recomendación mostrada'
    RECOMMENDATION_CLICKED = 'recommendation_clicked', 'Recomendación clickeada'
    BOOK_OPENED = 'book_opened', 'Libro abierto'
    WISHLIST_ADDED = 'wishlist_added', 'Añadido a lista de deseos'
    READING_STARTED = 'reading_started', 'Lectura iniciada'
    READING_FINISHED = 'reading_finished', 'Lectura finalizada'
    RATED = 'rated', 'Valorado'


class RecommendationFeedback(models.Model):
    """
    Registra eventos de interacción y conversión sobre libros recomendados para medir
    CTR, tasas de conversión (wishlist, lectura, finalización) y optimizar algoritmos.
    """
    recommendation_id = models.CharField(max_length=100, blank=True, default='', db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendation_feedbacks')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='recommendation_feedbacks')
    action = models.CharField(max_length=30, choices=RecommendationFeedbackAction.choices, db_index=True)
    strategy = models.CharField(max_length=50, blank=True, default='hybrid', db_index=True)
    algorithm_version = models.CharField(max_length=50, default='v1.0', db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action', '-created_at'], name='idx_recfb_user_act_date'),
            models.Index(fields=['book', 'action'], name='idx_recfb_book_act'),
            models.Index(fields=['algorithm_version', 'action'], name='idx_recfb_algo_act'),
            models.Index(fields=['strategy', 'action'], name='idx_recfb_strat_act'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.book.title} ({self.strategy})"


import re
import unicodedata

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
from mybookconnect.soft_delete import SoftDeleteModel


def normalize_isbn(value: str | None) -> str | None:
    """Normaliza un ISBN eliminando guiones, espacios y convirtiendo a mayúsculas."""
    if not value:
        return None
    cleaned = re.sub(r'[^0-9X]', '', str(value).upper().strip())
    return cleaned if cleaned else None


def normalize_title(value: str | None) -> str:
    """Normaliza un título eliminando acentos, caracteres no alfanuméricos y espacios repetidos para comparación."""
    if not value:
        return ""
    normalized = unicodedata.normalize('NFKD', str(value))
    ascii_clean = "".join(c for c in normalized if not unicodedata.combining(c))
    lowered = ascii_clean.lower().strip()
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', lowered)
    return " ".join(cleaned.split())


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
    nationality = models.CharField(max_length=100, blank=True, null=True, verbose_name='Nacionalidad / Origen')
    birth_date = models.DateField(blank=True, null=True, verbose_name='Fecha de nacimiento')
    death_date = models.DateField(blank=True, null=True, verbose_name='Fecha de fallecimiento')
    website = models.URLField(blank=True, null=True, verbose_name='Sitio web oficial')
    twitter = models.CharField(max_length=100, blank=True, null=True, verbose_name='Usuario de Twitter/X')
    instagram = models.CharField(max_length=100, blank=True, null=True, verbose_name='Usuario de Instagram')
    wikipedia_url = models.URLField(blank=True, null=True, verbose_name='Enlace a Wikipedia')
    canonical_name = models.CharField(max_length=200, blank=True, null=True, verbose_name='Nombre canónico')
    aliases = models.JSONField(default=list, blank=True, verbose_name='Alias y variantes de nombre')
    external_ids = models.JSONField(default=dict, blank=True, verbose_name='Identificadores externos')
    is_verified = models.BooleanField(default=False, db_index=True, verbose_name='Autor verificado')
    claimed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='claimed_authors',
        verbose_name='Usuario propietario verificado',
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

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=300)
    author = models.ForeignKey(Author, null=True, blank=True, on_delete=models.SET_NULL, related_name='books')
    authors = models.ManyToManyField(Author, related_name='all_books', blank=True)
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
    embedding = models.JSONField(null=True, blank=True, help_text="Vector de embedding semántico de la obra")
    additional_isbns = models.JSONField(
        default=list,
        blank=True,
        help_text="Listado de ISBNs adicionales o de otras ediciones (físico, digital, etc.)",
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title'], name='idx_book_title'),
            models.Index(fields=['title', 'author'], name='idx_book_title_author'),
            models.Index(fields=['-created_at'], name='idx_book_created_at'),
            models.Index(fields=['author', '-created_at'], name='idx_book_author_created'),
            GinIndex(fields=['title'], name='idx_book_title_trgm', opclasses=['gin_trgm_ops']),
            GinIndex(fields=['description'], name='idx_book_desc_trgm', opclasses=['gin_trgm_ops']),
        ]

    def get_author_names(self) -> str:
        """Devuelve los nombres de todos los autores concatenados por comas."""
        if hasattr(self, '_prefetched_objects_cache') and 'authors' in self._prefetched_objects_cache:
            author_names = [a.name for a in self.authors.all()]
        else:
            author_names = list(self.authors.values_list('name', flat=True))
        if author_names:
            return ", ".join(author_names)
        if self.author:
            return self.author.name
        return "Autor desconocido"

    def add_isbn(self, new_isbn: str | None) -> bool:
        """Añade un nuevo ISBN a la ficha del libro evitando duplicados."""
        cleaned = normalize_isbn(new_isbn)
        if not cleaned:
            return False
        if not self.isbn:
            self.isbn = cleaned
            return True
        if self.isbn == cleaned:
            return False
        if not isinstance(self.additional_isbns, list):
            self.additional_isbns = []
        if cleaned not in self.additional_isbns:
            self.additional_isbns.append(cleaned)
            return True
        return False

    def get_all_isbns(self) -> list[str]:
        """Devuelve todos los ISBNs asociados a esta obra (principal y alternativos)."""
        isbns = []
        if self.isbn:
            isbns.append(self.isbn)
        if isinstance(self.additional_isbns, list):
            for extra in self.additional_isbns:
                if extra and extra not in isbns:
                    isbns.append(extra)
        return isbns

    @classmethod
    def find_by_isbn(cls, isbn_candidate: str | None):
        """Busca un libro tanto por su ISBN principal como por sus ISBNs secundarios/alternativos."""
        cleaned = normalize_isbn(isbn_candidate)
        if not cleaned:
            return None
        found = cls.objects.filter(isbn=cleaned).first()
        if found:
            return found
        return cls.objects.filter(additional_isbns__contains=cleaned).first()

    def save(self, *args, **kwargs):
        if self.isbn:
            self.isbn = normalize_isbn(self.isbn)
        if isinstance(self.additional_isbns, list):
            clean_extras = []
            for item in self.additional_isbns:
                c = normalize_isbn(item)
                if c and c != self.isbn and c not in clean_extras:
                    clean_extras.append(c)
            self.additional_isbns = clean_extras
        super().save(*args, **kwargs)
        if self.author_id:
            self.authors.add(self.author)

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
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación personal privada de 1 a 5 estrellas.",
    )
    is_digital = models.BooleanField(default=False)
    owned = models.BooleanField(default=False)
    wishlist = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_user_book'),
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5) | models.Q(rating__isnull=True),
                name='check_userbook_rating_range_1_to_5',
            ),
        ]
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['user', 'book']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'wishlist']),
            models.Index(fields=['is_read', '-updated_at'], name='idx_userbook_read_updated'),
            models.Index(fields=['status', '-updated_at'], name='idx_userbook_status_updated'),
            models.Index(fields=['book', 'status'], name='idx_userbook_book_status'),
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


class Review(SoftDeleteModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Calificación pública de 1 a 5 estrellas.",
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    text = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='reviews/',
        null=True,
        blank=True,
        validators=[validate_cover_image],
        help_text="Fotografía o imagen adjunta a la reseña (ej. portada, dedicatoria, pasaje; máx 10MB)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_moderated = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si la reseña ha sido ocultada por moderación",
    )


    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'book'],
                condition=models.Q(deleted_at__isnull=True),
                name='unique_active_review_user_book',
            ),
            models.CheckConstraint(
                check=models.Q(rating__gte=1, rating__lte=5),
                name='check_review_rating_range_1_to_5',
            ),
        ]
        indexes = [
            models.Index(fields=['book', '-created_at'], name='idx_review_book_created'),
            models.Index(fields=['user', '-created_at'], name='idx_review_user_created'),
            models.Index(fields=['-created_at'], name='idx_review_created_at'),
            models.Index(fields=['book', 'deleted_at'], name='idx_review_book_del'),
            models.Index(fields=['user', 'deleted_at'], name='idx_review_user_del'),
            models.Index(fields=['book', 'rating'], name='idx_review_book_rating'),
            models.Index(fields=['user', 'book'], name='idx_review_user_book'),
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


class ReviewComment(SoftDeleteModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='review_comments')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='erratas', null=True, blank=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='erratas', null=True, blank=True)
    type = models.CharField(max_length=20, choices=ErrataType.choices, default=ErrataType.ERRATA)
    status = models.CharField(max_length=20, choices=ErrataStatus.choices, default=ErrataStatus.OPEN)
    text = models.TextField()
    resolution_notes = models.TextField(blank=True, null=True)
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='resolved_erratas',
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at'], name='idx_errata_status_created'),
            models.Index(fields=['book', 'status'], name='idx_errata_book_status'),
            models.Index(fields=['author', 'status'], name='idx_errata_author_status'),
        ]

    def __str__(self):
        target = self.book.title if self.book else (self.author.name if self.author else 'General')
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
        review_avg = Review.objects.filter(
            book=book, rating__isnull=False, deleted_at__isnull=True, is_moderated=False
        ).aggregate(Avg('rating'))['rating__avg']
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
        from .cache_utils import cascade_book_invalidation
        cascade_book_invalidation(instance.id)
    except Exception:
        pass


@receiver(post_save, sender=Review)
@receiver(post_delete, sender=Review)
def handle_review_signals(sender, instance, **kwargs):
    created = kwargs.get('created', False)
    # Ejecuta cascada completa de invalidación reactiva (Roadmap Fase 65)
    try:
        from .cache_utils import cascade_review_invalidation
        cascade_review_invalidation(instance.book_id, instance.user_id)
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
    # Invalida caché de perfil, estadísticas, recomendaciones, feed y libro (Fase 8 - 13.3)
    try:
        from .cache_utils import cascade_reading_status_invalidation
        cascade_reading_status_invalidation(instance.user_id, instance.book_id)
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
        ('content_policy', 'Política de Contenido'),
        ('deletion_policy', 'Política de Eliminación y Retención'),
        ('contact', 'Contacto y Soporte Legal'),
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
    is_moderated = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si la lista ha sido ocultada por el equipo de moderación",
    )
    is_collaborative = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Lista colaborativa",
        help_text="Permite que otros usuarios invitados colaboren añadiendo y organizando libros",
    )
    views_count = models.PositiveIntegerField(
        default=0,
        help_text="Número de veces que la lista ha sido abierta/consultada",
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
            models.Index(fields=['is_moderated', '-updated_at'], name='idx_readinglist_mod_updated'),
            models.Index(fields=['is_collaborative', '-updated_at'], name='idx_readinglist_collab_updated'),
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
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='added_reading_list_items',
        verbose_name="Añadido por",
        help_text="Usuario que aportó este libro a la lista (dueño o colaborador)",
    )
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


class ReadingListCollaborator(models.Model):
    """
    Colaborador invitado a una lista de lectura colaborativa (RoadmapV3 Sección 30.2).
    """
    class Role(models.TextChoices):
        EDITOR = 'EDITOR', 'Editor'
        VIEWER = 'VIEWER', 'Lector'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Invitación pendiente'
        ACCEPTED = 'ACCEPTED', 'Aceptada'
        REJECTED = 'REJECTED', 'Rechazada'

    reading_list = models.ForeignKey(
        ReadingList,
        on_delete=models.CASCADE,
        related_name='collaborators',
        verbose_name='Lista de lectura',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collaborations',
        verbose_name='Usuario colaborador',
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.EDITOR,
        verbose_name='Rol de colaboración',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name='Estado de la invitación',
    )
    can_add_books = models.BooleanField(
        default=True,
        verbose_name='Puede añadir libros',
    )
    can_remove_books = models.BooleanField(
        default=False,
        verbose_name='Puede eliminar libros de otros',
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sent_collaborations',
        verbose_name='Invitado por',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de invitación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Colaborador de Lista'
        verbose_name_plural = 'Colaboradores de Listas'
        unique_together = ('reading_list', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} en {self.reading_list.name} [{self.status}]"


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


class ReadingListComment(SoftDeleteModel):
    """
    Comentario social dentro de una lista de lectura pública o de seguidos (Fase 21).
    Permite debatir e intercambiar opiniones sobre selecciones de libros.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_list_comments')
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(help_text="Contenido del comentario sobre la lista")
    is_moderated = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si el comentario ha sido ocultado por el equipo de moderación",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['reading_list', 'created_at'], name='idx_rlcomment_list_created'),
            models.Index(fields=['reading_list', 'deleted_at'], name='idx_rlcomment_list_del'),
        ]

    def __str__(self):
        return f"Comentario de {self.user.username} en Lista {self.reading_list_id}"


class RecommendationFeedbackAction(models.TextChoices):
    RECOMMENDATION_SHOWN = 'recommendation_shown', 'Recomendación mostrada'
    RECOMMENDATION_CLICKED = 'recommendation_clicked', 'Recomendación clickeada'
    BOOK_OPENED = 'book_opened', 'Libro abierto'
    WISHLIST_ADDED = 'wishlist_added', 'Añadido a lista de deseos'
    READING_STARTED = 'reading_started', 'Lectura iniciada'
    READING_FINISHED = 'reading_finished', 'Lectura finalizada'
    RATED = 'rated', 'Valorado'
    DISMISSED = 'dismissed', 'Descartado'


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


class EmbeddingStatus(models.TextChoices):
    PENDING = 'pending', 'Pendiente'
    COMPLETED = 'completed', 'Completado'
    FAILED = 'failed', 'Fallido'
    STALE = 'stale', 'Desactualizado'


class BookEmbedding(models.Model):
    """
    Modelo satélite para persistencia vectorial y metadatos de embeddings de libros (Fase 6 - 11.5).
    Mantiene la tabla principal de libros liviana y registra el ciclo de vida de vectorización.
    """
    book = models.OneToOneField(
        Book,
        on_delete=models.CASCADE,
        related_name='embedding_record',
        verbose_name='Libro asociado',
    )
    vector = models.JSONField(default=list, blank=True, verbose_name='Vector de embedding')
    dimension = models.PositiveIntegerField(default=768, verbose_name='Dimensión del vector')
    embedding_model = models.CharField(
        max_length=128,
        default='nomic-embed-text',
        verbose_name='Modelo generador',
    )
    embedding_version = models.CharField(
        max_length=32,
        default='v1.0',
        verbose_name='Versión del pipeline',
    )
    embedded_at = models.DateTimeField(null=True, blank=True, verbose_name='Fecha de vectorización')
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING,
        db_index=True,
        verbose_name='Estado del embedding',
    )
    content_hash = models.CharField(
        max_length=64,
        blank=True,
        default='',
        db_index=True,
        verbose_name='Hash SHA256 del contenido fuente',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Embedding de Libro'
        verbose_name_plural = 'Embeddings de Libros'
        indexes = [
            models.Index(fields=['embedding_status', 'embedded_at'], name='idx_emb_status_date'),
            models.Index(fields=['embedding_model', 'embedding_version'], name='idx_emb_mod_ver'),
        ]

    def __str__(self) -> str:
        return f"Embedding [{self.embedding_status}] - {self.book.title} ({self.dimension}d)"



# ==============================================================================
# Plataforma de Autores y Monetización (Fase 31 — RoadmapV2)
# ==============================================================================

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
        Author,
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
        verbose_name = 'Perfil de Autor'
        verbose_name_plural = 'Perfiles de Autores'

    def __str__(self) -> str:
        name = self.pen_name or (self.author.name if self.author else self.user.username)
        return f"Perfil de Autor: {name} ({'Verificado' if self.is_verified else 'Pendiente'})"


class AuthorAnnouncement(models.Model):
    """
    Publicación oficial, comunicado o adelanto literario publicado por un autor para sus lectores.
    RoadmapV3 Sección 30 — Sprint 12 (Publicaciones avanzadas de autores).
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
        Author,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='announcements',
        verbose_name='Autor del catálogo',
    )
    book = models.ForeignKey(
        Book,
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
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Fecha de publicación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
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
        Author,
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
        Book,
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
        verbose_name = 'Asistente a Evento'
        verbose_name_plural = 'Asistentes a Eventos'
        constraints = [
            models.UniqueConstraint(fields=['event', 'user'], name='unique_event_user_attendance'),
        ]
        ordering = ['created_at']

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.event.title} ({self.get_status_display()})"


class AffiliateClick(models.Model):
    """
    Registro anónimo de clics en enlaces de afiliados para telemetría y métricas de conversión.
    No almacena PII para cumplir estrictamente con el RGPD.
    """
    class FormatChoices(models.TextChoices):
        PAPERBACK = 'paperback', 'Libro Físico'
        EBOOK = 'ebook', 'Ebook Kindle'
        AUDIOBOOK = 'audiobook', 'Audiolibro Audible'

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='affiliate_clicks',
        verbose_name='Libro consultado',
    )
    format = models.CharField(
        max_length=20,
        choices=FormatChoices.choices,
        default=FormatChoices.PAPERBACK,
        db_index=True,
        verbose_name='Formato de compra',
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True, verbose_name='Fecha del clic')

    class Meta:
        verbose_name = 'Clic de Afiliado'
        verbose_name_plural = 'Clics de Afiliados'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Clic [{self.format}] - {self.book.title} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class AuthorClaimStatus(models.TextChoices):
    PENDING = 'pending', 'Pendiente'
    APPROVED = 'approved', 'Aprobada'
    REJECTED = 'rejected', 'Rechazada'
    CANCELLED = 'cancelled', 'Cancelada'


class AuthorClaim(models.Model):
    """
    Solicitud formal de un usuario registrado para reclamar la autoría y página de un autor.
    RoadmapV3 Sprint 3 (Sección 4.4).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='author_claims',
        verbose_name='Usuario solicitante',
    )
    author = models.ForeignKey(
        Author,
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
        verbose_name = 'Reclamación de Autor'
        verbose_name_plural = 'Reclamaciones de Autores'
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Reclamación: {self.user.username} -> {self.author.name} [{self.status}]"


class FAQ(models.Model):
    """
    Pregunta y respuesta frecuente gestionable por administradores y visualizable en acordeón.
    RoadmapV3 Sprint 3.
    """
    class Category(models.TextChoices):
        GENERAL = 'general', 'General'
        AUTHORS = 'authors', 'Autores y Verificación'
        BOOKS = 'books', 'Libros y Biblioteca'
        ACCOUNT = 'account', 'Cuenta y Privacidad'
        COMMUNITY = 'community', 'Comunidad y Red Social'

    question = models.CharField(max_length=300, verbose_name='Pregunta')
    answer = models.TextField(verbose_name='Respuesta')
    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.GENERAL,
        db_index=True,
        verbose_name='Categoría temática',
    )
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name='Orden')
    is_published = models.BooleanField(default=True, db_index=True, verbose_name='Publicada')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Fecha de creación')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Última actualización')

    class Meta:
        verbose_name = 'Pregunta Frecuente (FAQ)'
        verbose_name_plural = 'Preguntas Frecuentes (FAQs)'
        ordering = ['order', 'id']

    def __str__(self) -> str:
        return self.question


# Modelos de gamificación opcional (Fase 54)
from .gamification_models import (  # noqa: E402, F401
    Badge,
    BadgeCategory,
    ChallengeType,
    DailyReadingLog,
    ReadingChallenge,
    ReadingGoal,
    ReadingStreak,
    UserBadge,
    UserChallenge,
)

# Modelos de Clubs de Lectura y Debates (RoadmapV3 Sección 30.1)
from .club_models import (  # noqa: E402, F401
    ReadingClub,
    ReadingClubMember,
    ReadingClubBook,
    ReadingClubDiscussion,
    ReadingClubDiscussionComment,
)





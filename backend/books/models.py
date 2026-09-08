from django.db import models
from django.conf import settings
from django.db.models import Avg
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import datetime


class Author(models.Model):
    name = models.CharField(max_length=200)
    biography = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='author_photos/', null=True, blank=True)
    enrichment_attempted = models.BooleanField(default=False)

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
    cover = models.ImageField(upload_to='covers/', null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    published_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=datetime.utcnow)
    average_rating = models.FloatField(null=True, blank=True)
    categories = models.ManyToManyField(Category, related_name='books', blank=True)

    def __str__(self):
        return f"{self.title}"


class UserBook(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_books')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='user_entries')
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
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['user', 'wishlist']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reseña {self.user.username} - {self.book.title}"


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
            models.Index(fields=['status']),
        ]

    def __str__(self):
        target = self.book.title if self.book else (self.author.name if self.author else 'N/A')
        return f"{self.type} - {target} ({self.status})"


@receiver(post_save, sender=UserBook)
@receiver(post_delete, sender=UserBook)
def update_book_rating(sender, instance, **kwargs):
    book = instance.book
    avg = UserBook.objects.filter(book=book, rating__isnull=False).aggregate(Avg('rating'))['rating__avg']
    book.average_rating = round(avg, 2) if avg else None
    book.save(update_fields=['average_rating'])


@receiver(post_save, sender=UserBook)
def sync_userbook_to_review(sender, instance, **kwargs):
    if instance.rating is not None:
        Review.objects.update_or_create(
            user=instance.user,
            book=instance.book,
            defaults={
                'text': instance.notes or '',
                'rating': instance.rating
            }
        )
    else:
        Review.objects.filter(user=instance.user, book=instance.book).delete()


@receiver(post_delete, sender=UserBook)
def delete_review_on_userbook_delete(sender, instance, **kwargs):
    Review.objects.filter(user=instance.user, book=instance.book).delete()

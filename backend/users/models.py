from datetime import date

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models


class PrivacyChoices(models.TextChoices):
    PUBLIC = 'public', 'Público'
    FRIENDS = 'friends', 'Solo amigos'
    PRIVATE = 'private', 'Privado'

class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email = models.EmailField(unique=True, blank=False, null=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    blocked_users = models.ManyToManyField('self', symmetrical=False, related_name='blocked_by', blank=True)
    is_editor = models.BooleanField(default=False)

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

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator
from datetime import date

class PrivacyChoices(models.TextChoices):
    PUBLIC = 'public', 'Público'
    FRIENDS = 'friends', 'Solo amigos'
    PRIVATE = 'private', 'Privado'

class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email = models.EmailField(unique=True, blank=False, null=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    
    # Nuevos campos
    birth_date = models.DateField(null=True, blank=True, 
        validators=[MinValueValidator(limit_value=date(1900, 1, 1))])
    location = models.CharField(max_length=100, blank=True)
    privacy_level = models.CharField(
        max_length=10,
        choices=PrivacyChoices.choices,
        default=PrivacyChoices.PUBLIC
    )
    
    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.username

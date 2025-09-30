from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]

    email = models.EmailField(_('email address'), unique=True)
    birth_date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, null=True, blank=True)
    privacy_level = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    class Meta:
        db_table = 'auth_user'
        swappable = 'AUTH_USER_MODEL'

    def __str__(self):
        return self.username
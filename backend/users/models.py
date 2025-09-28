from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    email = models.EmailField(unique=True, blank=False, null=False)
    following = models.ManyToManyField('self', symmetrical=False, related_name='followers', blank=True)
    is_private = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.username

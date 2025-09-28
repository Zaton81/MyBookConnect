from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal para realizar acciones cuando se crea un usuario nuevo
    Por ejemplo, crear un perfil asociado o enviar email de bienvenida
    """
    if created:
        # Aquí puedes agregar lógica adicional cuando se crea un usuario
        pass
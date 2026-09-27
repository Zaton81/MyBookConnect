from django.conf import settings
from django.db import models
from django.utils import timezone

from mybookconnect.media_security import validate_chat_image
from mybookconnect.soft_delete import SoftDeleteManager, SoftDeleteModel

User = settings.AUTH_USER_MODEL


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('id',)

    def __str__(self):
        return f"Conversación {self.id}"

    @classmethod
    def get_or_create_direct(cls, user1, user2):
        """
        Devuelve la conversación 1:1 canónica existente entre user1 y user2,
        o crea una nueva garantizando que A <-> B y B <-> A resuelvan a la misma.
        Sincroniza además los estados de ConversationParticipant para cada usuario.
        """
        from django.db import transaction

        if not user1 or not user2 or user1.id == user2.id:
            raise ValueError("Se requieren dos usuarios distintos para una conversación directa")

        with transaction.atomic():
            existing = (
                cls.objects.filter(participants=user1)
                .filter(participants=user2)
                .first()
            )
            if existing:
                ConversationParticipant.objects.get_or_create(conversation=existing, user=user1)
                ConversationParticipant.objects.get_or_create(conversation=existing, user=user2)
                return existing, False

            conv = cls.objects.create()
            conv.participants.add(user1, user2)
            ConversationParticipant.objects.get_or_create(conversation=conv, user=user1)
            ConversationParticipant.objects.get_or_create(conversation=conv, user=user2)
            return conv, True


class ConversationParticipant(models.Model):
    """
    Estado y cursor de lectura de un participante dentro de una conversación.
    Permite tracking granular de último mensaje leído y lectura multiusuario (Fase 4).
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='participant_states',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_participations',
    )
    last_read_message = models.ForeignKey(
        'Message',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+',
    )
    last_read_at = models.DateTimeField(null=True, blank=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['conversation', 'user'], name='idx_conv_part_user'),
        ]

    def __str__(self):
        return f"Participante {self.user_id} en Conversación {self.conversation_id}"


class Message(SoftDeleteModel):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    client_message_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Identificador único generado por el cliente para deduplicación idempotente.",
    )
    text = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='chat_images/',
        null=True,
        blank=True,
        validators=[validate_chat_image],
        help_text="Imagen del chat (JPEG, PNG, WebP; máx 10MB; dimensiones 50x50 a 6000x6000px)",
    )
    created_at = models.DateTimeField(default=timezone.now)
    read = models.BooleanField(default=False)
    is_moderated = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indica si el mensaje ha sido ocultado por moderación",
    )

    objects = SoftDeleteManager()

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at'], name='idx_msg_conv_created'),
            models.Index(fields=['conversation', 'read'], name='idx_msg_conv_read'),
            models.Index(fields=['conversation', 'deleted_at'], name='idx_msg_conv_del'),
            models.Index(fields=['conversation', 'client_message_id'], name='idx_msg_conv_client_id'),
        ]

    def __str__(self):
        return f"Mensaje de {self.sender} en {self.conversation.id}"

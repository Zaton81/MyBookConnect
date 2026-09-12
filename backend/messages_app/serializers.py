from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Conversation, Message

User = get_user_model()


class ChatUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from books.media_utils import build_media_url
        if instance.avatar:
            ret['avatar'] = build_media_url(instance.avatar, request=request)
        return ret


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.PrimaryKeyRelatedField(read_only=True)
    sender_details = ChatUserSerializer(source='sender', read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_details', 'text', 'image', 'created_at', 'read']
        read_only_fields = ['id', 'sender', 'created_at', 'read']

    def validate_image(self, value):
        """
        Valida y sanitiza la imagen adjunta en el mensaje de chat.
        Asegura formato permitido, dimensiones, cuota <= 10MB y elimina metadatos EXIF.
        """
        if not value:
            return value
        from django.core.exceptions import ValidationError as DjangoValidationError

        from mybookconnect.media_security import sanitize_image, validate_chat_image

        try:
            validate_chat_image(value)
            return sanitize_image(value)
        except DjangoValidationError as err:
            msg = err.messages if hasattr(err, 'messages') else str(err)
            raise serializers.ValidationError(msg) from err

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from books.media_utils import build_media_url
        if instance.image:
            ret['image'] = build_media_url(instance.image, request=request)
        return ret


class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    participants_details = ChatUserSerializer(source='participants', many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'participants_details', 'created_at', 'updated_at', 'last_message', 'unread_count']

    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        return MessageSerializer(last).data if last else None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(read=False).exclude(sender=request.user).count()
        return 0

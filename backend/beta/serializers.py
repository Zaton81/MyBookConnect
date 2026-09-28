from rest_framework import serializers
from .models import (
    BetaFeedback,
    BetaFeedbackCategory,
    BetaFeedbackStatus,
    BetaInvitation,
    SupportTicket,
)


class BetaFeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BetaFeedback
        fields = [
            'id',
            'category',
            'title',
            'description',
            'page_url',
            'device_info',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_title(self, value):
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError("El título debe tener al menos 3 caracteres.")
        return cleaned

    def validate_description(self, value):
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise serializers.ValidationError("La descripción debe tener al menos 5 caracteres.")
        return cleaned


class BetaFeedbackAdminSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)

    class Meta:
        model = BetaFeedback
        fields = [
            'id',
            'user',
            'user_username',
            'user_email',
            'category',
            'title',
            'description',
            'page_url',
            'device_info',
            'status',
            'admin_notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'user_username', 'user_email', 'category', 'title', 'description', 'page_url', 'device_info', 'created_at', 'updated_at']


class BetaInvitationSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, default=None)
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = BetaInvitation
        fields = [
            'id',
            'code',
            'invited_email',
            'max_uses',
            'uses_count',
            'is_active',
            'is_valid',
            'expires_at',
            'created_by',
            'created_by_username',
            'created_at',
        ]
        read_only_fields = ['id', 'uses_count', 'created_by', 'created_by_username', 'created_at', 'is_valid']

    def get_is_valid(self, obj) -> bool:
        return obj.is_valid()


class VerifyBetaInvitationSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64, required=True)

    def validate_code(self, value):
        cleaned = value.strip()
        try:
            invitation = BetaInvitation.objects.get(code=cleaned)
        except BetaInvitation.DoesNotExist:
            raise serializers.ValidationError("Código de invitación inválido o inexistente.")

        if not invitation.is_valid():
            raise serializers.ValidationError("Este código de invitación ha expirado o ha alcanzado su límite de usos.")

        return cleaned


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'subject',
            'message',
            'category',
            'priority',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']

    def validate_subject(self, value):
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError("El asunto debe contener al menos 3 caracteres.")
        return cleaned

    def validate_message(self, value):
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise serializers.ValidationError("El mensaje debe contener al menos 5 caracteres.")
        return cleaned


class SupportTicketDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'subject',
            'message',
            'category',
            'status',
            'priority',
            'admin_response',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'subject', 'message', 'category', 'created_at', 'updated_at']


class SupportTicketAdminSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True, default=None)
    user_email = serializers.CharField(source='user.email', read_only=True, default=None)

    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'user',
            'user_username',
            'user_email',
            'subject',
            'message',
            'category',
            'status',
            'priority',
            'admin_response',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'user_username', 'user_email', 'subject', 'message', 'created_at', 'updated_at']

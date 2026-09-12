"""
Serializadores para consulta de la bitácora de auditoría (Fase 30).
"""

from rest_framework import serializers

from .models import AuditLog


class AuditLogListSerializer(serializers.ModelSerializer):
    """Serializador para listados tabulares en el visor de auditoría."""
    actor_username = serializers.CharField(source='actor.username', read_only=True, default='Sistema')
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            'id',
            'actor',
            'actor_username',
            'action',
            'action_display',
            'target_type',
            'object_id',
            'target_repr',
            'ip_address',
            'created_at',
        )

    def get_target_type(self, obj) -> str:
        if not obj.content_type:
            return 'general'
        return obj.content_type.model


class AuditLogDetailSerializer(AuditLogListSerializer):
    """Serializador detallado con carga completa de metadatos y cliente."""

    class Meta(AuditLogListSerializer.Meta):
        fields = AuditLogListSerializer.Meta.fields + ('user_agent', 'metadata')

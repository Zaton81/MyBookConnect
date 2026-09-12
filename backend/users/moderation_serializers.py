"""
Serializadores dedicados para el sistema de moderación y denuncias (Fase 29).

Permite:
- Validación rigurosa al denunciar usuarios, reseñas, comentarios y mensajes de chat.
- Prohibición estricta de auto-denuncias (un usuario no puede reportar su propio contenido).
- Prevención de reportes duplicados pendientes sobre el mismo objeto por el mismo denunciante.
- Representación enriquecida para moderadores con vista previa del contenido denunciado.
- Serialización de acciones disciplinarias y resolución de expedientes de moderación.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from books.models import Review, ReviewComment
from messages_app.models import Message
from users.models import Report, ReportStatus

User = get_user_model()

# Mapeo canónico de tipos de contenido denunciables
ALLOWED_TARGET_MODELS = {
    'user': User,
    'review': Review,
    'comment': ReviewComment,
    'message': Message,
}


class ReportCreateSerializer(serializers.ModelSerializer):
    """
    Serializador para que los usuarios autenticados creen un nuevo reporte de moderación.
    """
    target_type = serializers.ChoiceField(
        choices=list(ALLOWED_TARGET_MODELS.keys()),
        write_only=True,
        help_text="Tipo de contenido denunciado: user, review, comment, message",
    )
    object_id = serializers.IntegerField(
        help_text="ID primario del elemento denunciado",
    )

    class Meta:
        model = Report
        fields = ('id', 'target_type', 'object_id', 'reason', 'description', 'status', 'created_at')
        read_only_fields = ('id', 'status', 'created_at')

    def validate(self, attrs):
        """Valida que el contenido exista, no sea del propio denunciante y no esté duplicado."""
        request = self.context.get('request')
        user = getattr(request, 'user', None)

        target_type = attrs.get('target_type')
        object_id = attrs.get('object_id')

        model_class = ALLOWED_TARGET_MODELS.get(target_type)
        if not model_class:
            raise serializers.ValidationError({"target_type": "Tipo de contenido no admitido para moderación."})

        # Comprobar existencia del objeto denunciado
        try:
            target_obj = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            raise serializers.ValidationError({"object_id": f"El objeto {target_type} con ID {object_id} no existe."}) from None

        # Prohibir auto-denuncias
        if user and user.is_authenticated:
            is_self = False
            if target_type == 'user' and target_obj.id == user.id:
                is_self = True
            elif target_type in ('review', 'comment') and getattr(target_obj, 'user_id', None) == user.id:
                is_self = True
            elif target_type == 'message' and getattr(target_obj, 'sender_id', None) == user.id:
                is_self = True

            if is_self:
                raise serializers.ValidationError("No puedes denunciar tu propio contenido o perfil.")

            # Evitar denuncias duplicadas pendientes
            ct = ContentType.objects.get_for_model(model_class)
            pending_exists = Report.objects.filter(
                reporter=user,
                content_type=ct,
                object_id=object_id,
                status__in=[ReportStatus.OPEN, ReportStatus.UNDER_REVIEW],
            ).exists()

            if pending_exists:
                raise serializers.ValidationError("Ya tienes una denuncia activa en trámite para este elemento.")

        attrs['content_object_instance'] = target_obj
        attrs['content_type_model'] = model_class
        return attrs

    def create(self, validated_data):
        """Persiste el reporte asignando el content_type y reporter."""
        model_class = validated_data.pop('content_type_model')
        validated_data.pop('content_object_instance')
        validated_data.pop('target_type')

        reporter = self.context['request'].user
        content_type = ContentType.objects.get_for_model(model_class)

        return Report.objects.create(
            reporter=reporter,
            content_type=content_type,
            **validated_data,
        )


class ReportListSerializer(serializers.ModelSerializer):
    """Serializador para listados en la cola de moderación."""
    reporter_username = serializers.CharField(source='reporter.username', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    target_type = serializers.SerializerMethodField()
    target_preview = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = (
            'id', 'reporter', 'reporter_username', 'target_type', 'object_id',
            'reason', 'reason_display', 'description', 'status', 'status_display',
            'action_taken', 'target_preview', 'created_at', 'resolved_at',
        )

    def get_target_type(self, obj) -> str:
        """Devuelve el nombre legible del tipo de objeto denunciado."""
        if not obj.content_type:
            return 'unknown'
        model_name = obj.content_type.model
        if model_name == 'reviewcomment':
            return 'comment'
        return model_name

    def get_target_preview(self, obj) -> dict:
        """Genera una vista previa del objeto denunciado."""
        target = obj.content_object
        if not target:
            return {"deleted": True, "summary": "El objeto ha sido eliminado"}

        if isinstance(target, User):
            return {
                "type": "user",
                "username": target.username,
                "email": target.email,
                "is_active": target.is_active,
                "role": getattr(target, 'role', 'USER'),
            }
        elif isinstance(target, Review):
            return {
                "type": "review",
                "author": target.user.username,
                "book_title": target.book.title,
                "rating": target.rating,
                "snippet": (target.text[:120] + '...') if target.text and len(target.text) > 120 else target.text,
                "is_moderated": target.is_moderated,
            }
        elif isinstance(target, ReviewComment):
            return {
                "type": "comment",
                "author": target.user.username,
                "snippet": (target.content[:120] + '...') if target.content and len(target.content) > 120 else target.content,
                "is_deleted": bool(target.deleted_at),
            }
        elif isinstance(target, Message):
            return {
                "type": "message",
                "sender": target.sender.username,
                "snippet": (target.text[:120] + '...') if target.text and len(target.text) > 120 else target.text,
                "has_image": bool(target.image),
                "is_moderated": target.is_moderated,
            }
        return {"summary": str(target)}


class ReportDetailSerializer(ReportListSerializer):
    """Serializador detallado para inspección exhaustiva de una denuncia."""
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True)

    class Meta:
        model = Report
        fields = ReportListSerializer.Meta.fields + ('resolution_notes', 'resolved_by', 'resolved_by_username', 'updated_at')


class ReportResolveSerializer(serializers.ModelSerializer):
    """Serializador para resolución y aplicación de medidas disciplinarias."""
    status = serializers.ChoiceField(choices=[ReportStatus.UNDER_REVIEW, ReportStatus.RESOLVED, ReportStatus.REJECTED])
    action_taken = serializers.ChoiceField(
        choices=['HIDE_CONTENT', 'BAN_USER', 'DISMISS', 'WARNING', ''],
        required=False,
        allow_blank=True,
    )
    resolution_notes = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Report
        fields = ('status', 'action_taken', 'resolution_notes')

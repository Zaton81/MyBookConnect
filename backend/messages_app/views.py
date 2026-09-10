from django.contrib.auth import get_user_model
from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from books.pagination import StandardCursorPagination

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()

class IsParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        from users.policies import can_access_conversation

        conv = obj if isinstance(obj, Conversation) else getattr(obj, 'conversation', None)
        return can_access_conversation(request.user, conv)

class ConversationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages').order_by('-updated_at')

    @action(detail=False, methods=['post'], url_path='start')
    def start_conversation(self, request):
        from users.policies import can_message

        other_id = request.data.get('user_id')
        if not other_id:
            return Response({'error': 'user_id requerido'}, status=400)
        other = User.objects.filter(id=other_id).first()
        if not other:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        if not can_message(request.user, other):
            return Response({'error': 'No puedes chatear con este usuario debido a una restricción o bloqueo'}, status=403)

        conv, _ = Conversation.get_or_create_direct(request.user, other)
        return Response({'conversation_id': conv.id})

class MessageViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = StandardCursorPagination

    def get_queryset(self):
        conv_id = self.request.query_params.get('conversation')
        if not conv_id:
            return Message.objects.none()
        conv = Conversation.objects.filter(id=conv_id, participants=self.request.user).first()
        if not conv:
            return Message.objects.none()
        return Message.objects.filter(conversation=conv).select_related('sender')

    def perform_create(self, serializer):
        from users.models import Notification, NotificationType
        from users.policies import can_access_conversation, can_message

        conv_id = self.request.data.get('conversation')
        conv = Conversation.objects.filter(id=conv_id).first()
        if not conv or not can_access_conversation(self.request.user, conv):
            raise serializers.ValidationError('Conversación no encontrada o sin permisos')
        # Verificar que no exista bloqueo activo con los participantes
        for participant in conv.participants.exclude(id=self.request.user.id):
            if not can_message(self.request.user, participant):
                raise serializers.ValidationError('No puedes enviar mensajes a esta conversación debido a una restricción de privacidad o bloqueo.')

        msg = serializer.save(sender=self.request.user, conversation=conv)

        # Generar notificación para los demás participantes
        for participant in conv.participants.exclude(id=self.request.user.id):
            Notification.objects.create(
                recipient=participant,
                actor=self.request.user,
                type=NotificationType.MESSAGE,
                title=f'Mensaje de {self.request.user.username}',
                message=msg.text[:80] if msg.text else 'Te ha enviado una imagen',
                link=f'/chat?conversationId={conv.id}',
            )

from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer

User = get_user_model()

class IsParticipant(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.participants.all()

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages').order_by('-updated_at')

    @action(detail=False, methods=['post'], url_path='start')
    def start_conversation(self, request):
        other_id = request.data.get('user_id')
        if not other_id:
            return Response({'error': 'user_id requerido'}, status=400)
        other = User.objects.filter(id=other_id).first()
        if not other:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        # Solo permitir si son amigos mutuos
        if not (other in request.user.following.all() and request.user in other.following.all()):
            return Response({'error': 'Solo puedes chatear con amigos mutuos'}, status=403)
        # Buscar conversación existente
        conv = Conversation.objects.filter(participants=request.user).filter(participants=other).first()
        if not conv:
            conv = Conversation.objects.create()
            conv.participants.add(request.user, other)
        return Response({'conversation_id': conv.id})

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsParticipant]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        conv_id = self.request.query_params.get('conversation')
        if not conv_id:
            return Message.objects.none()
        conv = Conversation.objects.filter(id=conv_id, participants=self.request.user).first()
        if not conv:
            return Message.objects.none()
        return Message.objects.filter(conversation=conv).select_related('sender')

    def perform_create(self, serializer):
        conv_id = self.request.data.get('conversation')
        conv = Conversation.objects.filter(id=conv_id, participants=self.request.user).first()
        if not conv:
            raise serializers.ValidationError('Conversación no encontrada o sin permisos')
        serializer.save(sender=self.request.user, conversation=conv)

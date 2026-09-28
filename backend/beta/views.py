from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from .models import BetaFeedback, BetaInvitation
from .serializers import (
    BetaFeedbackAdminSerializer,
    BetaFeedbackCreateSerializer,
    BetaInvitationSerializer,
    VerifyBetaInvitationSerializer,
)


class BetaFeedbackCreateView(generics.CreateAPIView):
    """
    Endpoint para que los usuarios autenticados envíen feedback durante la beta cerrada.
    """
    serializer_class = BetaFeedbackCreateSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def perform_create(self, serializer):
        page_url = self.request.data.get('page_url')
        if not page_url:
            page_url = self.request.META.get('HTTP_REFERER', '')[:500]

        device_info = self.request.data.get('device_info')
        if not device_info:
            device_info = self.request.META.get('HTTP_USER_AGENT', '')[:255]

        serializer.save(
            user=self.request.user,
            page_url=page_url,
            device_info=device_info,
        )


class BetaFeedbackAdminListView(generics.ListAPIView):
    """
    Listado filtrable de incidencias y feedback para el equipo de administración.
    """
    serializer_class = BetaFeedbackAdminSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = BetaFeedback.objects.select_related('user').all()
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        status_val = self.request.query_params.get('status')
        if status_val:
            qs = qs.filter(status=status_val)
        return qs


class BetaFeedbackAdminDetailView(generics.RetrieveUpdateAPIView):
    """
    Detalle y actualización de triaje (estado y notas de moderación) por administradores.
    """
    queryset = BetaFeedback.objects.select_related('user').all()
    serializer_class = BetaFeedbackAdminSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'patch']


class BetaInvitationAdminView(generics.ListCreateAPIView):
    """
    Administración de códigos de invitación para la cohorte beta.
    """
    queryset = BetaInvitation.objects.select_related('created_by').all()
    serializer_class = BetaInvitationSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class VerifyBetaInvitationView(APIView):
    """
    Verificación pública de código de invitación antes del registro en la beta.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyBetaInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data['code']
        invitation = BetaInvitation.objects.get(code=code)
        return Response({
            'valid': True,
            'code': invitation.code,
            'invited_email': invitation.invited_email,
            'max_uses': invitation.max_uses,
            'uses_remaining': max(0, invitation.max_uses - invitation.uses_count),
        }, status=status.HTTP_200_OK)

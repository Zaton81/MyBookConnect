from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from .models import BetaFeedback, BetaInvitation, SupportTicket
from .serializers import (
    BetaFeedbackAdminSerializer,
    BetaFeedbackCreateSerializer,
    BetaInvitationSerializer,
    SupportTicketAdminSerializer,
    SupportTicketCreateSerializer,
    SupportTicketDetailSerializer,
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

        feedback = serializer.save(
            user=self.request.user,
            page_url=page_url,
            device_info=device_info,
        )
        from .alerts_service import BetaAlertsService
        BetaAlertsService.process_feedback_submission(feedback)


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


class SupportTicketCreateView(generics.CreateAPIView):
    """
    Creación de tickets de asistencia o soporte formal por usuarios autenticados (Fase 28).
    """
    serializer_class = SupportTicketCreateSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def perform_create(self, serializer):
        ticket = serializer.save(user=self.request.user)
        from .alerts_service import BetaAlertsService
        BetaAlertsService.process_support_ticket_submission(ticket)


class UserSupportTicketListView(generics.ListAPIView):
    """
    Listado de tickets de soporte creados por el usuario autenticado.
    """
    serializer_class = SupportTicketDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user).order_by('-created_at')


class AdminSupportTicketListView(generics.ListAPIView):
    """
    Cola global de tickets de soporte para el equipo de administración (Fase 28).
    """
    serializer_class = SupportTicketAdminSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = SupportTicket.objects.select_related('user').all()
        status_val = self.request.query_params.get('status')
        if status_val:
            qs = qs.filter(status=status_val)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        priority = self.request.query_params.get('priority')
        if priority:
            qs = qs.filter(priority=priority)
        return qs


class AdminSupportTicketDetailView(generics.RetrieveUpdateAPIView):
    """
    Detalle y resolución/respuesta a tickets de soporte por administradores.
    """
    queryset = SupportTicket.objects.select_related('user').all()
    serializer_class = SupportTicketAdminSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'patch']


class BetaCohortMetricsAdminView(APIView):
    """
    Telemetría agregada y métricas de activación de la cohorte beta para administradores (Fase 36).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .metrics_service import BetaMetricsService
        return Response(BetaMetricsService.get_cohort_summary_metrics(), status=status.HTTP_200_OK)


class AdminBetaAlertsView(APIView):
    """
    Listado de alertas operativas e incidencias críticas sin resolver para el equipo de guardia (Fase 36).
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from .alerts_service import BetaAlertsService
        alerts = BetaAlertsService.get_active_alerts()
        return Response({'count': len(alerts), 'alerts': alerts}, status=status.HTTP_200_OK)

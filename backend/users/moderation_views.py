"""
Vistas para la gestión de denuncias y moderación de contenido (Fase 29).

Proporciona:
- Endpoints para que los usuarios autenticados reporten contenido abusivo o antirreglamentario.
- Cola de moderación para administradores y moderadores con filtrado por estado, motivo y tipo.
- Tramitación y resolución de denuncias con aplicación inmediata de sanciones disciplinarias:
  - Ocultación de reseñas, comentarios o mensajes (HIDE_CONTENT).
  - Suspensión o baneo de usuarios infractores (BAN_USER).
  - Desestimación justificada de reportes infundados (DISMISS).
- Métricas y estadísticas de la cola de moderación.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books.admin_views import IsModeratorOrAdmin
from books.models import Review, ReviewComment
from books.pagination import StandardResultsSetPagination
from messages_app.models import Message
from users.models import Report, ReportStatus

from .moderation_serializers import (
    ALLOWED_TARGET_MODELS,
    ReportCreateSerializer,
    ReportDetailSerializer,
    ReportListSerializer,
    ReportResolveSerializer,
)

User = get_user_model()


class ReportCreateView(generics.CreateAPIView):
    """
    Endpoint para que usuarios autenticados denuncien un contenido o usuario.
    POST /api/v1/reports/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportCreateSerializer


class UserReportsListView(generics.ListAPIView):
    """
    Endpoint para que un usuario consulte el estado de las denuncias que ha presentado.
    GET /api/v1/reports/my/
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReportListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Report.objects.filter(reporter=self.request.user).select_related('reporter', 'content_type')


class AdminReportListView(generics.ListAPIView):
    """
    Cola de moderación administrativa con filtros de búsqueda.
    GET /api/v1/admin/reports/
    """
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = ReportListSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = Report.objects.all().select_related('reporter', 'content_type', 'resolved_by')

        status_param = self.request.query_params.get('status')
        if status_param and status_param != 'all':
            qs = qs.filter(status=status_param.upper())

        reason_param = self.request.query_params.get('reason')
        if reason_param and reason_param != 'all':
            qs = qs.filter(reason=reason_param.upper())

        target_type = self.request.query_params.get('target_type')
        if target_type and target_type in ALLOWED_TARGET_MODELS:
            model_class = ALLOWED_TARGET_MODELS[target_type]
            ct = ContentType.objects.get_for_model(model_class)
            qs = qs.filter(content_type=ct)

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(description__icontains=search)
                | Q(reporter__username__icontains=search)
                | Q(resolution_notes__icontains=search)
            )

        return qs.order_by('-created_at')


class AdminReportDetailView(generics.RetrieveUpdateAPIView):
    """
    Detalle, tramitación y resolución de una denuncia administrativa.
    GET /api/v1/admin/reports/<int:pk>/
    PATCH /api/v1/admin/reports/<int:pk>/
    """
    permission_classes = [IsModeratorOrAdmin]
    serializer_class = ReportDetailSerializer
    queryset = Report.objects.all().select_related('reporter', 'content_type', 'resolved_by')

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()

        serializer = ReportResolveSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data.get('status', instance.status)
        action_taken = serializer.validated_data.get('action_taken', instance.action_taken)
        resolution_notes = serializer.validated_data.get('resolution_notes', instance.resolution_notes)

        instance.status = new_status
        instance.action_taken = action_taken
        instance.resolution_notes = resolution_notes

        # Si se resuelve o rechaza, registrar moderador y marca temporal
        if new_status in [ReportStatus.RESOLVED, ReportStatus.REJECTED]:
            instance.resolved_by = request.user
            instance.resolved_at = timezone.now()

        # Ejecutar sanciones disciplinarias según la acción seleccionada
        if new_status == ReportStatus.RESOLVED:
            target = instance.content_object

            if action_taken == 'HIDE_CONTENT' and target:
                if isinstance(target, Review):
                    target.is_moderated = True
                    target.save(update_fields=['is_moderated'])
                elif isinstance(target, ReviewComment):
                    target.deleted_at = timezone.now()
                    target.save(update_fields=['deleted_at'])
                elif isinstance(target, Message):
                    target.is_moderated = True
                    target.save(update_fields=['is_moderated'])

            elif action_taken == 'BAN_USER' and target:
                user_to_ban = None
                if isinstance(target, User):
                    user_to_ban = target
                elif isinstance(target, (Review, ReviewComment)):
                    user_to_ban = target.user
                elif isinstance(target, Message):
                    user_to_ban = target.sender

                if user_to_ban and not (user_to_ban.is_staff or user_to_ban.is_superuser):
                    user_to_ban.is_active = False
                    user_to_ban.save(update_fields=['is_active'])

        instance.save()
        return Response(ReportDetailSerializer(instance).data, status=status.HTTP_200_OK)


class AdminModerationStatsView(APIView):
    """
    Métricas cuantitativas de la cola de moderación.
    GET /api/v1/admin/reports/stats/
    """
    permission_classes = [IsModeratorOrAdmin]

    def get(self, request):
        total_reports = Report.objects.count()
        open_reports = Report.objects.filter(status=ReportStatus.OPEN).count()
        under_review_reports = Report.objects.filter(status=ReportStatus.UNDER_REVIEW).count()
        resolved_reports = Report.objects.filter(status=ReportStatus.RESOLVED).count()
        rejected_reports = Report.objects.filter(status=ReportStatus.REJECTED).count()

        by_reason = dict(
            Report.objects.values('reason').annotate(count=Count('id')).values_list('reason', 'count')
        )

        return Response({
            "total": total_reports,
            "total_reports": total_reports,
            "open_reports": open_reports,
            "under_review_reports": under_review_reports,
            "resolved_reports": resolved_reports,
            "rejected_reports": rejected_reports,
            "by_status": {
                "open": open_reports,
                "under_review": under_review_reports,
                "resolved": resolved_reports,
                "rejected": rejected_reports,
            },
            "by_reason": by_reason,
        })

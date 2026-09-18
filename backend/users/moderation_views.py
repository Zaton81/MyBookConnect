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
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Report.objects.none()
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

            elif action_taken == 'RESTORE_CONTENT' and target:
                if isinstance(target, Review):
                    target.is_moderated = False
                    target.save(update_fields=['is_moderated'])
                elif isinstance(target, ReviewComment):
                    target.deleted_at = None
                    target.save(update_fields=['deleted_at'])
                elif isinstance(target, Message):
                    target.is_moderated = False
                    target.save(update_fields=['is_moderated'])

            elif action_taken in ('BAN_USER', 'MUTE_USER_24H', 'MUTE_USER_7D') and target:
                user_to_act = None
                if isinstance(target, User):
                    user_to_act = target
                elif isinstance(target, (Review, ReviewComment)):
                    user_to_act = target.user
                elif isinstance(target, Message):
                    user_to_act = target.sender

                if user_to_act and not (user_to_act.is_staff or user_to_act.is_superuser):
                    if action_taken == 'BAN_USER':
                        user_to_act.is_active = False
                        user_to_act.save(update_fields=['is_active'])
                    elif action_taken == 'MUTE_USER_24H':
                        user_to_act.muted_until = timezone.now() + timezone.timedelta(hours=24)
                        user_to_act.save(update_fields=['muted_until'])
                    elif action_taken == 'MUTE_USER_7D':
                        user_to_act.muted_until = timezone.now() + timezone.timedelta(days=7)
                        user_to_act.save(update_fields=['muted_until'])

        instance.save()

        # Registro de auditoría
        from users.audit_service import log_audit
        from users.models import AuditAction

        audit_action = AuditAction.MODERATION_RESOLVE if new_status == ReportStatus.RESOLVED else AuditAction.MODERATION_REJECT
        log_audit(
            action=audit_action,
            actor=request.user,
            target=instance,
            request=request,
            metadata={
                "report_id": instance.id,
                "status": new_status,
                "action_taken": action_taken,
                "target_type": instance.content_type.model if instance.content_type else None,
                "target_id": instance.object_id,
                "resolution_notes": resolution_notes,
            },
        )

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


class AdminContentHideView(APIView):
    """
    Ocultación directa de contenido infractor (Fase 58).
    POST /api/v1/admin/moderation/hide/
    Payload: { "target_type": "review" | "comment" | "message", "target_id": <int>, "reason": <str> }
    """
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request):
        from users.audit_service import log_audit
        from users.models import AuditAction

        target_type = request.data.get('target_type')
        target_id = request.data.get('target_id')
        reason = request.data.get('reason', 'Ocultado por moderación')

        if not target_type or not target_id:
            return Response({'detail': 'target_type y target_id son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

        target = None
        if target_type == 'review':
            target = Review.objects.filter(id=target_id).first()
            if not target:
                return Response({'detail': 'Reseña no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            target.is_moderated = True
            target.save(update_fields=['is_moderated'])
        elif target_type == 'comment':
            target = ReviewComment.objects.filter(id=target_id).first()
            if not target:
                return Response({'detail': 'Comentario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            target.deleted_at = timezone.now()
            target.save(update_fields=['deleted_at'])
        elif target_type == 'message':
            target = Message.objects.filter(id=target_id).first()
            if not target:
                return Response({'detail': 'Mensaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            target.is_moderated = True
            target.save(update_fields=['is_moderated'])
        else:
            return Response({'detail': f"target_type no válido: {target_type}"}, status=status.HTTP_400_BAD_REQUEST)

        log_audit(
            action=AuditAction.CONTENT_HIDE,
            actor=request.user,
            target=target,
            request=request,
            metadata={"target_type": target_type, "target_id": target_id, "reason": reason},
        )
        return Response({'detail': f"Elemento {target_type} #{target_id} ocultado correctamente.", "hidden": True}, status=status.HTTP_200_OK)


class AdminContentRestoreView(APIView):
    """
    Restauración directa de contenido previamente moderado u ocultado (Fase 58).
    POST /api/v1/admin/moderation/restore/
    Payload: { "target_type": "review" | "comment" | "message", "target_id": <int> }
    """
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request):
        from users.audit_service import log_audit
        from users.models import AuditAction

        target_type = request.data.get('target_type')
        target_id = request.data.get('target_id')

        if not target_type or not target_id:
            return Response({'detail': 'target_type y target_id son requeridos.'}, status=status.HTTP_400_BAD_REQUEST)

        target = None
        if target_type == 'review':
            target = Review.objects.filter(id=target_id).first()
            if not target:
                return Response({'detail': 'Reseña no encontrada.'}, status=status.HTTP_404_NOT_FOUND)
            target.is_moderated = False
            target.save(update_fields=['is_moderated'])
        elif target_type == 'comment':
            target = ReviewComment.objects.filter(id=target_id).first()
            if not target:
                return Response({'detail': 'Comentario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            target.deleted_at = None
            target.save(update_fields=['deleted_at'])
        elif target_type == 'message':
            target = Message.objects.filter(id=target_id).first()
            if not target:
                return Response({'detail': 'Mensaje no encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            target.is_moderated = False
            target.save(update_fields=['is_moderated'])
        else:
            return Response({'detail': f"target_type no válido: {target_type}"}, status=status.HTTP_400_BAD_REQUEST)

        log_audit(
            action=AuditAction.CONTENT_RESTORE,
            actor=request.user,
            target=target,
            request=request,
            metadata={"target_type": target_type, "target_id": target_id},
        )
        return Response({'detail': f"Elemento {target_type} #{target_id} restaurado correctamente.", "hidden": False}, status=status.HTTP_200_OK)


class AdminUserMuteView(APIView):
    """
    Silenciamiento disciplinario de un usuario por parte de un moderador (Fase 58).
    POST /api/v1/admin/moderation/users/<int:user_id>/mute/
    Payload: { "duration_hours": <int, opcional>, "reason": <str> }
    """
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, user_id):
        from users.audit_service import log_audit
        from users.models import AuditAction

        user_to_mute = User.objects.filter(id=user_id).first()
        if not user_to_mute:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if user_to_mute.is_superuser or user_to_mute.is_staff:
            return Response({'detail': 'No se puede aplicar silenciamiento disciplinario a administradores o miembros del staff.'}, status=status.HTTP_400_BAD_REQUEST)

        duration_hours = request.data.get('duration_hours')
        reason = request.data.get('reason', 'Silenciamiento disciplinario')

        if duration_hours and int(duration_hours) > 0:
            user_to_mute.muted_until = timezone.now() + timezone.timedelta(hours=int(duration_hours))
        else:
            # Permanente / Indefinido (10 años)
            user_to_mute.muted_until = timezone.now() + timezone.timedelta(days=3650)

        user_to_mute.save(update_fields=['muted_until'])

        log_audit(
            action=AuditAction.MODERATOR_MUTE,
            actor=request.user,
            target=user_to_mute,
            request=request,
            metadata={
                "target_username": user_to_mute.username,
                "muted_until": user_to_mute.muted_until.isoformat(),
                "reason": reason,
            },
        )

        return Response({
            'detail': f"Usuario @{user_to_mute.username} silenciado disciplinariamente hasta {user_to_mute.muted_until.isoformat()}.",
            'muted_until': user_to_mute.muted_until,
            'is_disciplinary_muted': True,
        }, status=status.HTTP_200_OK)


class AdminUserUnmuteView(APIView):
    """
    Levantamiento del silenciamiento disciplinario de un usuario (Fase 58).
    POST /api/v1/admin/moderation/users/<int:user_id>/unmute/
    """
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, user_id):
        from users.audit_service import log_audit
        from users.models import AuditAction

        user_to_unmute = User.objects.filter(id=user_id).first()
        if not user_to_unmute:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        user_to_unmute.muted_until = None
        user_to_unmute.save(update_fields=['muted_until'])

        log_audit(
            action=AuditAction.MODERATOR_UNMUTE,
            actor=request.user,
            target=user_to_unmute,
            request=request,
            metadata={"target_username": user_to_unmute.username},
        )

        return Response({
            'detail': f"Silenciamiento disciplinario revocado para @{user_to_unmute.username}.",
            'muted_until': None,
            'is_disciplinary_muted': False,
        }, status=status.HTTP_200_OK)


class AdminUserBanView(APIView):
    """
    Suspensión/bloqueo de cuenta de usuario por moderación (Fase 58).
    POST /api/v1/admin/moderation/users/<int:user_id>/ban/
    Payload: { "reason": <str> }
    """
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, user_id):
        from users.audit_service import log_audit
        from users.models import AuditAction

        user_to_ban = User.objects.filter(id=user_id).first()
        if not user_to_ban:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if user_to_ban == request.user:
            return Response({'detail': 'No puedes auto-suspender tu propia cuenta.'}, status=status.HTTP_400_BAD_REQUEST)

        if user_to_ban.is_superuser or user_to_ban.is_staff:
            return Response({'detail': 'No se puede suspender a administradores o miembros del staff.'}, status=status.HTTP_400_BAD_REQUEST)

        reason = request.data.get('reason', 'Suspensión de cuenta por moderación')
        user_to_ban.is_active = False
        user_to_ban.save(update_fields=['is_active'])

        log_audit(
            action=AuditAction.USER_BAN,
            actor=request.user,
            target=user_to_ban,
            request=request,
            metadata={"target_username": user_to_ban.username, "reason": reason},
        )

        return Response({
            'detail': f"Usuario @{user_to_ban.username} suspendido exitosamente.",
            'is_active': False,
        }, status=status.HTTP_200_OK)


class AdminUserUnbanView(APIView):
    """
    Reactivación de cuenta de usuario suspendida (Fase 58).
    POST /api/v1/admin/moderation/users/<int:user_id>/unban/
    """
    permission_classes = [IsModeratorOrAdmin]

    def post(self, request, user_id):
        from users.audit_service import log_audit
        from users.models import AuditAction

        user_to_unban = User.objects.filter(id=user_id).first()
        if not user_to_unban:
            return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        user_to_unban.is_active = True
        user_to_unban.save(update_fields=['is_active'])

        log_audit(
            action=AuditAction.USER_UNBAN,
            actor=request.user,
            target=user_to_unban,
            request=request,
            metadata={"target_username": user_to_unban.username},
        )

        return Response({
            'detail': f"Cuenta de @{user_to_unban.username} reactivada exitosamente.",
            'is_active': True,
        }, status=status.HTTP_200_OK)

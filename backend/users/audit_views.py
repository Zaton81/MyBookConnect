"""
Vistas de administración para consulta y análisis de la bitácora de auditoría (Fase 30).
"""

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .audit_serializers import AuditLogDetailSerializer, AuditLogListSerializer
from .models import AuditLog, UserRole


class IsAdminOnly(permissions.BasePermission):
    """Permiso estricto reservado exclusivamente a Administradores y Superusuarios."""

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return (
            getattr(user, 'is_superuser', False)
            or getattr(user, 'is_staff', False)
            or getattr(user, 'role', None) == UserRole.ADMIN
        )


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminAuditLogListView(APIView):
    """
    Listado paginado y filtrable de registros de auditoría.
    GET /api/v1/admin/audit-logs/
    """
    permission_classes = [IsAdminOnly]

    def get(self, request):
        queryset = AuditLog.objects.select_related('actor', 'content_type').all()

        action = request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        actor_query = request.query_params.get('actor')
        if actor_query:
            if actor_query.isdigit():
                queryset = queryset.filter(actor_id=int(actor_query))
            else:
                queryset = queryset.filter(actor__username__icontains=actor_query)

        target_type = request.query_params.get('target_type')
        if target_type:
            queryset = queryset.filter(content_type__model=target_type.lower())

        date_from = request.query_params.get('date_from')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(target_repr__icontains=search)

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = AuditLogListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminAuditLogDetailView(APIView):
    """
    Detalle completo de un registro de auditoría individual.
    GET /api/v1/admin/audit-logs/<id>/
    """
    permission_classes = [IsAdminOnly]

    def get(self, request, pk):
        try:
            log_entry = AuditLog.objects.select_related('actor', 'content_type').get(pk=pk)
        except AuditLog.DoesNotExist:
            return Response({"detail": "Registro de auditoría no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AuditLogDetailSerializer(log_entry)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminAuditLogStatsView(APIView):
    """
    Estadísticas cuantitativas agregadas de eventos de auditoría.
    GET /api/v1/admin/audit-logs/stats/
    """
    permission_classes = [IsAdminOnly]

    def get(self, request):
        now = timezone.now()
        since_24h = now - timedelta(hours=24)
        since_7d = now - timedelta(days=7)

        total_logs = AuditLog.objects.count()
        logs_24h = AuditLog.objects.filter(created_at__gte=since_24h).count()
        logs_7d = AuditLog.objects.filter(created_at__gte=since_7d).count()

        by_action = dict(
            AuditLog.objects.values('action')
            .annotate(count=Count('id'))
            .values_list('action', 'count')
        )

        top_actors_qs = (
            AuditLog.objects.exclude(actor=None)
            .values('actor__username')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        top_actors = [{"username": item['actor__username'], "count": item['count']} for item in top_actors_qs]

        return Response({
            "total": total_logs,
            "last_24h": logs_24h,
            "last_7d": logs_7d,
            "by_action": by_action,
            "top_actors": top_actors,
        }, status=status.HTTP_200_OK)

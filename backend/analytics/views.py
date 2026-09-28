"""
Vistas de API para recolección de eventos y consulta de métricas de embudo (Fase 26).
"""

import logging
from datetime import datetime

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.models import ProductEventType
from analytics.services import AnalyticsService

logger = logging.getLogger(__name__)


class AnalyticsCollectView(APIView):
    """
    Ingesta de eventos de interacción desde el frontend o clientes API.
    Acepta eventos tanto de usuarios autenticados como anónimos (visitas previas al registro).
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Ingesta de eventos de producto",
        description="Registra un evento de interacción cuantitativo (vistas, recomendaciones, lecturas).",
        request=inline_serializer(
            name='AnalyticsCollectRequest',
            fields={
                'event_type': serializers.ChoiceField(choices=ProductEventType.choices),
                'session_id': serializers.CharField(required=False, allow_blank=True),
                'metadata': serializers.DictField(required=False),
                'async_mode': serializers.BooleanField(required=False, default=False),
            },
        ),
        responses={
            201: inline_serializer(
                name='AnalyticsCollectResponse',
                fields={'status': serializers.CharField(), 'event_id': serializers.IntegerField()},
            ),
            202: inline_serializer(
                name='AnalyticsCollectAsyncResponse',
                fields={'status': serializers.CharField(), 'enqueued': serializers.BooleanField()},
            ),
            400: OpenApiResponse(description="Tipo de evento inválido"),
        },
        tags=['Analytics'],
    )
    def post(self, request):
        event_type = request.data.get('event_type')
        if not event_type or event_type not in ProductEventType.values:
            return Response(
                {'detail': f"Tipo de evento '{event_type}' no válido. Opciones: {list(ProductEventType.values)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session_id = request.data.get('session_id', '')
        metadata = request.data.get('metadata') or {}
        async_mode = bool(request.data.get('async_mode', False))

        if async_mode:
            from analytics.tasks import record_analytics_event_task

            user_id = request.user.id if request.user.is_authenticated else None
            record_analytics_event_task.delay(
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                metadata=metadata,
            )
            return Response({'status': 'accepted', 'enqueued': True}, status=status.HTTP_202_ACCEPTED)

        ev = AnalyticsService.track_event(
            event_type=event_type,
            user=request.user if request.user.is_authenticated else None,
            session_id=session_id,
            metadata=metadata,
            request=request,
        )
        return Response({'status': 'created', 'event_id': ev.id}, status=status.HTTP_201_CREATED)


class AnalyticsFunnelView(APIView):
    """
    Consulta las etapas y ratios de conversión del embudo de producto (Fase 26).
    Exclusivo para administradores y equipo de producto.
    """
    permission_classes = (permissions.IsAdminUser,)

    @extend_schema(
        summary="Métricas de embudo de conversión y retención",
        description="Retorna los volúmenes por etapa del embudo (visit -> signup -> activation -> retention) y ratios.",
        parameters=[
            OpenApiParameter('start_date', str, description="Fecha inicial en formato YYYY-MM-DD", required=False),
            OpenApiParameter('end_date', str, description="Fecha final en formato YYYY-MM-DD", required=False),
        ],
        responses={
            200: inline_serializer(
                name='AnalyticsFunnelResponse',
                fields={
                    'funnel_steps': serializers.DictField(),
                    'conversion_rates': serializers.DictField(),
                },
            ),
            403: OpenApiResponse(description="Permiso denegado"),
        },
        tags=['Analytics'],
    )
    def get(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        start_dt = None
        end_dt = None
        try:
            if start_date_str:
                start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            if end_date_str:
                end_dt = datetime.strptime(end_date_str, '%Y-%m-%d')
        except ValueError:
            return Response(
                {'detail': "Formato de fecha inválido. Utiliza el estándar ISO YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = AnalyticsService.get_funnel_metrics(start_date=start_dt, end_date=end_dt)
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsSummaryView(APIView):
    """
    Resumen cuantitativo del volumen de eventos de producto registrados.
    Exclusivo para administradores.
    """
    permission_classes = (permissions.IsAdminUser,)

    @extend_schema(
        summary="Resumen de eventos de producto",
        description="Muestra el conteo de eventos totales, usuarios activos únicos y desglose por tipo.",
        responses={
            200: inline_serializer(
                name='AnalyticsSummaryResponse',
                fields={
                    'total_events': serializers.IntegerField(),
                    'unique_active_users': serializers.IntegerField(),
                    'events_by_type': serializers.DictField(),
                },
            )
        },
        tags=['Analytics'],
    )
    def get(self, request):
        data = AnalyticsService.get_event_summary()
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsRetentionView(APIView):
    """
    Métricas de retención de cohortes D1, D7 y D30 para usuarios registrados (Fase 28).
    Exclusivo para administradores.
    """
    permission_classes = (permissions.IsAdminUser,)

    @extend_schema(
        summary="Métricas de retención de cohortes",
        description="Calcula la tasa de retención activa en D1, D7 y D30 para los usuarios registrados en los últimos N días.",
        parameters=[
            OpenApiParameter('days', int, description="Ventana de tiempo en días (por defecto 30)", required=False),
        ],
        responses={
            200: inline_serializer(
                name='AnalyticsRetentionResponse',
                fields={
                    'timeframe_days': serializers.IntegerField(),
                    'total_signups': serializers.IntegerField(),
                    'd1_active_users': serializers.IntegerField(),
                    'd1_retention_rate': serializers.FloatField(),
                    'd7_active_users': serializers.IntegerField(),
                    'd7_retention_rate': serializers.FloatField(),
                    'd30_active_users': serializers.IntegerField(),
                    'd30_retention_rate': serializers.FloatField(),
                },
            )
        },
        tags=['Analytics'],
    )
    def get(self, request):
        try:
            days = int(request.query_params.get('days', 30))
            if days <= 0:
                days = 30
        except ValueError:
            days = 30

        data = AnalyticsService.get_retention_metrics(days=days)
        return Response(data, status=status.HTTP_200_OK)

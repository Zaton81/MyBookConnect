"""
Vistas de API para las funcionalidades de Inteligencia Artificial (Fases 26 y 27).

Expone endpoints para consulta de estado de proveedores, asistente conversacional
BookAI contextualizado, análisis temático de libros, búsqueda semántica y
ejecución controlada de herramientas seguras (Function Calling).
"""

import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.policies import (
    AIPolicyViolationError,
    AIRateLimitExceededError,
    validate_forbidden_client_parameters,
)
from ai.services import (
    execute_assistant_tool,
    get_ai_status,
    get_assistant_reply,
    get_available_assistant_tools,
    get_book_ai_summary,
    semantic_search_books,
)
from ai.tools import ToolExecutionError, ToolPermissionDeniedError
from books.models import Book
from books.serializers import BookSerializer

logger = logging.getLogger(__name__)


class AIStatusView(APIView):
    """
    Informa sobre el estado operativo del motor de IA (proveedor configurado,
    modelo activo, conectividad online/offline).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Estado del servicio de IA",
        description="Retorna la configuración y disponibilidad del proveedor de IA en tiempo real.",
        responses={
            200: inline_serializer(
                name='AIStatusResponse',
                fields={
                    'enabled': serializers.BooleanField(),
                    'is_online': serializers.BooleanField(),
                    'provider': serializers.CharField(),
                    'chat_model': serializers.CharField(),
                },
            )
        },
        tags=['AI'],
    )
    def get(self, request):
        """
        Retorna la configuración y disponibilidad del proveedor de IA en tiempo real.

        :param request: Objeto HttpRequest autenticado.
        :return: Response con enabled, is_online, provider, chat_model, etc.
        """
        status_data = get_ai_status()
        return Response(status_data, status=status.HTTP_200_OK)


class AIAssistantView(APIView):
    """
    Asistente literario conversacional contextualizado con la biblioteca del usuario.
    Compatible con proveedores locales (Ollama) y en la nube (OpenAI, OpenRouter).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Chat con asistente literario BookAI",
        description="Procesa una consulta conversacional con el asistente BookAI contextualizado.",
        request=inline_serializer(
            name='AIAssistantRequest',
            fields={
                'messages': serializers.ListField(child=serializers.DictField()),
                'book_id': serializers.IntegerField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name='AIAssistantResponse',
                fields={
                    'message': serializers.DictField(),
                    'model': serializers.CharField(),
                    'provider': serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="Violación de políticas"),
            429: OpenApiResponse(description="Límite de tasa excedido"),
        },
        tags=['AI'],
    )
    def post(self, request):
        """
        Procesa una consulta conversacional con el asistente BookAI.

        :param request: Objeto HttpRequest con messages y contextBookId opcional en el cuerpo.
        :return: Response con el mensaje del asistente, modelo y metadatos de disponibilidad.
        """
        try:
            # Validación estricta contra inyección de parámetros de control del modelo (Sección 10.2)
            validate_forbidden_client_parameters(request.data)

            messages = request.data.get('messages', [])
            book_id = request.data.get('book_id')
            req_id = request.headers.get('X-Request-ID')

            reply_data = get_assistant_reply(
                user=request.user,
                raw_messages=messages,
                book_id=book_id,
                request_id=req_id,
            )
            response = Response(reply_data, status=status.HTTP_200_OK)
            if 'request_id' in reply_data:
                response['X-Request-ID'] = reply_data['request_id']
            return response
        except AIRateLimitExceededError as rate_err:
            response = Response(
                {
                    'detail': str(rate_err),
                    'window': getattr(rate_err, 'window', 'minute'),
                    'retry_after': getattr(rate_err, 'retry_after', 60),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
            response['Retry-After'] = str(getattr(rate_err, 'retry_after', 60))
            return response
        except AIPolicyViolationError as policy_err:
            return Response(
                {'detail': str(policy_err)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Error al procesar consulta del asistente de IA: %s", exc)
            return Response(
                {'detail': 'Error interno al procesar la consulta con el asistente de IA.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AISemanticSearchView(APIView):
    """
    Búsqueda semántica por conceptos, estados de ánimo o temáticas literarias.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Búsqueda semántica de libros",
        description="Busca libros por conceptos, estados de ánimo o temáticas literarias.",
        responses={
            200: inline_serializer(
                name='AISemanticSearchResponse',
                fields={
                    'query': serializers.CharField(),
                    'results': BookSerializer(many=True),
                    'count': serializers.IntegerField(),
                },
            ),
        },
        tags=['AI'],
    )
    def get(self, request):
        """
        Busca libros en la base de datos que coincidan semánticamente con la consulta.

        :param request: Objeto HttpRequest con parámetro 'query'.
        :return: Response con lista serializada de libros afines.
        """
        query = request.query_params.get('query', '').strip()
        if not query:
            return Response({'query': '', 'results': [], 'count': 0}, status=status.HTTP_200_OK)

        from books.services.unified_search_service import UnifiedSearchEngine
        engine = UnifiedSearchEngine(mode='semantic')
        books_qs = engine.search_queryset(query=query, limit=10, auto_import=False)
        if not books_qs.exists():
            books_qs = semantic_search_books(query=query, limit=10)

        serializer = BookSerializer(books_qs, many=True, context={'request': request})
        return Response({
            "query": query,
            "results": serializer.data,
            "count": books_qs.count(),
        }, status=status.HTTP_200_OK)


class AIBookSummaryView(APIView):
    """
    Genera un análisis y síntesis temática del libro vía IA.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Resumen temático generado por IA",
        description="Genera una ficha analítica y síntesis temática del libro especificado.",
        responses={
            200: inline_serializer(
                name='AIBookSummaryResponse',
                fields={
                    'summary': serializers.CharField(),
                    'themes': serializers.ListField(child=serializers.CharField()),
                    'provider': serializers.CharField(),
                },
            ),
            404: OpenApiResponse(description="Libro no encontrado"),
        },
        tags=['AI'],
    )
    def post(self, request, pk):
        """
        Genera una ficha analítica breve y objetiva del libro especificado.

        :param request: Objeto HttpRequest autenticado.
        :param pk: Clave primaria del libro a analizar.
        :return: Response con el texto analítico generado o fallback catalogado.
        """
        book = get_object_or_404(Book, pk=pk)
        summary_data = get_book_ai_summary(book=book)
        return Response(summary_data, status=status.HTTP_200_OK)


class AIToolsListView(APIView):
    """
    Retorna la lista de herramientas disponibles para el asistente en formato Function Calling.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Lista de herramientas de IA",
        description="Retorna la lista de herramientas disponibles para el asistente en formato Function Calling.",
        responses={
            200: inline_serializer(
                name='AIToolsListResponse',
                fields={
                    'tools': serializers.ListField(child=serializers.DictField()),
                    'count': serializers.IntegerField(),
                },
            ),
        },
        tags=['AI'],
    )
    def get(self, request):
        """
        Lista las definiciones de esquemas de herramientas seguras disponibles.

        :param request: Objeto HttpRequest autenticado.
        :return: Response con array de esquemas de tools compatibles con OpenAI.
        """
        tools = get_available_assistant_tools()
        return Response({"tools": tools, "count": len(tools)}, status=status.HTTP_200_OK)


class AIToolExecuteView(APIView):
    """
    Punto de entrada seguro para la ejecución de herramientas del asistente.
    El backend valida la identidad, permisos y argumentos antes de ejecutar cualquier acción.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Ejecutar herramienta de IA",
        description="Ejecuta una herramienta de asistencia literaria de forma segura y controlada.",
        request=inline_serializer(
            name='AIToolExecuteRequest',
            fields={
                'tool_name': serializers.CharField(),
                'arguments': serializers.DictField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name='AIToolExecuteResponse',
                fields={
                    'tool_name': serializers.CharField(),
                    'result': serializers.DictField(),
                    'status': serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="Parámetros inválidos"),
            403: OpenApiResponse(description="Permiso denegado"),
        },
        tags=['AI'],
    )
    def post(self, request):
        """
        Ejecuta una herramienta solicitada de forma controlada.

        :param request: Objeto HttpRequest con tool_name y arguments.
        :return: Response con el resultado de la ejecución.
        """
        tool_name = request.data.get('tool_name')
        arguments = request.data.get('arguments') or {}

        if not tool_name:
            return Response(
                {'detail': "El campo 'tool_name' es obligatorio."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = execute_assistant_tool(
                user=request.user,
                tool_name=tool_name,
                arguments=arguments,
            )
            return Response({
                "tool_name": tool_name,
                "result": result,
                "status": "success",
            }, status=status.HTTP_200_OK)
        except ToolPermissionDeniedError as perm_err:
            return Response(
                {'detail': str(perm_err)},
                status=status.HTTP_403_FORBIDDEN,
            )
        except ToolExecutionError as tool_err:
            return Response(
                {'detail': str(tool_err)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Error al ejecutar herramienta '%s': %s", tool_name, exc)
            return Response(
                {'detail': f"Error interno al ejecutar la herramienta: {str(exc)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

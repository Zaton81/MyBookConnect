"""
Vistas de API para las funcionalidades de Inteligencia Artificial (Fases 26 y 27).

Expone endpoints para consulta de estado de proveedores, asistente conversacional
BookAI contextualizado, análisis temático de libros, búsqueda semántica y
ejecución controlada de herramientas seguras (Function Calling).
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.policies import AIPolicyViolationError, AIRateLimitExceededError
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

    def post(self, request):
        """
        Procesa una consulta conversacional con el asistente BookAI.

        :param request: Objeto HttpRequest con messages y contextBookId opcional en el cuerpo.
        :return: Response con el mensaje del asistente, modelo y metadatos de disponibilidad.
        """
        messages = request.data.get('messages', [])
        book_id = request.data.get('book_id')

        try:
            reply_data = get_assistant_reply(
                user=request.user,
                raw_messages=messages,
                book_id=book_id,
            )
            return Response(reply_data, status=status.HTTP_200_OK)
        except AIRateLimitExceededError as rate_err:
            return Response(
                {'detail': str(rate_err)},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
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

    def get(self, request):
        """
        Busca libros en la base de datos que coincidan semánticamente con la consulta.

        :param request: Objeto HttpRequest con parámetro 'query'.
        :return: Response con lista serializada de libros afines.
        """
        query = request.query_params.get('query', '').strip()
        if not query:
            return Response({'query': '', 'results': [], 'count': 0}, status=status.HTTP_200_OK)

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

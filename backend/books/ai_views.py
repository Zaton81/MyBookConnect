"""
Vistas de API para las funcionalidades de Inteligencia Artificial (Fase 26).

Expone endpoints para consulta de estado de proveedores, asistente conversacional
BookAI contextualizado, análisis temático de libros y búsqueda semántica.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.policies import AIPolicyViolationError
from ai.services import (
    get_ai_status,
    get_assistant_reply,
    get_book_ai_summary,
    semantic_search_books,
)
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

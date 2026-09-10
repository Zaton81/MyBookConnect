import logging

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mybookconnect.ai_service import ai_client

from .models import Book, UserBook
from .serializers import BookSerializer

logger = logging.getLogger(__name__)


class AIStatusView(APIView):
    """
    Informa sobre el estado del motor de IA (proveedor configurado, modelo, online/offline).
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        is_online = ai_client.is_available()
        return Response({
            "enabled": ai_client.enabled,
            "is_online": is_online,
            "provider_url": ai_client.base_url,
            "chat_model": ai_client.model_chat,
            "embeddings_model": ai_client.model_embeddings,
        })


class AIAssistantView(APIView):
    """
    Asistente literario conversacional contextualizado con la biblioteca del usuario.
    Compatible con cualquier proveedor OpenAI (Ollama, OpenAI, Groq, etc.).
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        messages = request.data.get('messages', [])
        book_id = request.data.get('book_id')

        if not messages or not isinstance(messages, list):
            return Response(
                {'detail': 'Se requiere una lista de mensajes en formato [{"role": "user", "content": "..."}]'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Recopilar contexto del usuario
        user = request.user
        recent_read = UserBook.objects.filter(
            user=user, is_read=True
        ).select_related('book').order_by('-updated_at')[:5]

        read_titles = [ub.book.title for ub in recent_read if ub.book]

        context_lines = [
            f"El usuario actual es @{user.username}.",
        ]
        if read_titles:
            context_lines.append(f"Libros que ha leído recientemente: {', '.join(read_titles)}.")

        if book_id:
            book = Book.objects.filter(id=book_id).first()
            if book:
                context_lines.append(
                    f"El usuario está consultando específicamente sobre el libro '{book.title}' "
                    f"escrito por {book.author.name if book.author else 'desconocido'}. "
                    f"Descripción: {book.description[:300] if book.description else 'Sin descripción'}."
                )

        system_prompt = (
            "Eres BookAI, el asistente literario inteligente de MyBookConnect. "
            "Eres cordial, perspicaz, conciso y apasionado por los libros y la lectura. "
            "Recomienda libros basados en gustos, resuelve dudas sobre tramas sin spoilers mayores, "
            "compara obras o autores, y sugiere lecturas fascinantes. "
            "Responde en español y utiliza formato markdown elegante con negritas y listas cuando sea oportuno.\n\n"
            "Contexto de la conversación:\n" + "\n".join(context_lines)
        )

        ai_response = ai_client.chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=800,
        )

        # Si el modelo de IA no está disponible (ej. Ollama apagado), proveer fallback asistido
        if not ai_response.get("success"):
            suggested_books = Book.objects.all().order_by('-average_rating')[:3]
            fallback_titles = [f"**{b.title}** ({b.author.name if b.author else 'Varios'})" for b in suggested_books]

            fallback_content = (
                f"¡Hola {user.username}! Actualmente el motor de IA local no está respondiendo "
                f"(puedes iniciar Ollama en tu sistema con `ollama run {ai_client.model_chat}`).\n\n"
                f"Mientras tanto, aquí tienes libros muy aclamados por la comunidad de MyBookConnect:\n"
                + "\n".join([f"- {t}" for t in fallback_titles])
            )
            return Response({
                "message": {
                    "role": "assistant",
                    "content": fallback_content,
                },
                "provider": "fallback-system",
                "model": "rule-based",
                "ai_online": False,
            })

        return Response({
            "message": {
                "role": "assistant",
                "content": ai_response["content"],
            },
            "provider": ai_response.get("provider"),
            "model": ai_response.get("model"),
            "ai_online": True,
        })


class AISemanticSearchView(APIView):
    """
    Búsqueda semántica por conceptos, estados de ánimo o temáticas.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        query = request.query_params.get('query', '').strip()
        if not query:
            return Response({'results': []})

        # Buscar en título, descripción y categorías
        books = Book.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(categories__name__icontains=query) |
            Q(author__name__icontains=query)
        ).distinct().order_by('-average_rating')[:10]

        serializer = BookSerializer(books, many=True, context={'request': request})
        return Response({
            "query": query,
            "results": serializer.data,
            "count": books.count(),
        })


class AIBookSummaryView(APIView):
    """
    Genera un análisis y síntesis temática del libro vía IA.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)

        prompt = (
            f"Analiza el siguiente libro:\n"
            f"Título: {book.title}\n"
            f"Autor: {book.author.name if book.author else 'Desconocido'}\n"
            f"Sinopsis: {book.description or 'No disponible'}\n\n"
            f"Genera una ficha analítica breve con los siguientes puntos:\n"
            f"1. **Temas Centrales** (3 viñetas)\n"
            f"2. **Tono y Estilo Literario** (2 oraciones)\n"
            f"3. **Para quién es ideal esta lectura** (1 recomendación clave)"
        )

        response = ai_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="Eres un crítico literario experto y conciso.",
            max_tokens=500,
        )

        if response.get("success"):
            return Response({"summary": response["content"], "ai_online": True})
        else:
            fallback = (
                f"**Análisis de '{book.title}'**:\n\n"
                f"- **Género principal**: {', '.join([c.name for c in book.categories.all()]) or 'Literatura General'}\n"
                f"- **Sinopsis breve**: {book.description[:250] if book.description else 'Información en proceso de catalogación.'}...\n"
                f"- *(Inicia Ollama o configura un proveedor cloud para análisis neuronal profundo)*"
            )
            return Response({"summary": fallback, "ai_online": False})

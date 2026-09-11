"""
Servicios de alto nivel para interacción conversacional, análisis y búsqueda semántica con IA.
"""

import logging
from typing import Any

from django.db.models import Q

from ai.clients.factory import get_ai_provider
from ai.policies import validate_and_sanitize_chat_messages
from ai.prompts import build_assistant_system_prompt, build_book_summary_prompt
from books.models import Book, UserBook

logger = logging.getLogger(__name__)


def get_ai_status() -> dict[str, Any]:
    """
    Consulta el estado operativo, modelo activo y conectividad del proveedor de IA configurado.

    :return: Diccionario con el estado del proveedor.
    """
    provider = get_ai_provider()
    is_online = provider.is_available()
    return {
        "enabled": provider.enabled,
        "is_online": is_online,
        "provider": provider.name,
        "provider_url": provider.base_url,
        "chat_model": provider.model_chat,
        "embeddings_model": provider.model_embeddings,
    }


def get_assistant_reply(
    user: Any,
    raw_messages: list[dict[str, Any]],
    book_id: int | None = None,
) -> dict[str, Any]:
    """
    Orquesta la conversación con el asistente literario BookAI, aplicando validación
    de políticas, contextualización de lecturas del usuario y fallback en caso de desconexión.

    :param user: Instancia del usuario autenticado.
    :param raw_messages: Lista de mensajes recibida desde el frontend.
    :param book_id: ID opcional de libro sobre el que se formula la consulta.
    :return: Diccionario con la respuesta del asistente, metadatos y estado de disponibilidad.
    """
    # 1. Validación y sanitización estricta
    sanitized_messages = validate_and_sanitize_chat_messages(raw_messages)

    # 2. Recopilación de contexto de biblioteca del usuario
    recent_read = (
        UserBook.objects.filter(user=user, is_read=True)
        .select_related('book')
        .order_by('-updated_at')[:5]
    )
    read_titles = [ub.book.title for ub in recent_read if ub.book]

    current_book_info = None
    if book_id:
        book = Book.objects.filter(id=book_id).select_related('author').first()
        if book:
            current_book_info = {
                'title': book.title,
                'author_name': book.author.name if book.author else 'desconocido',
                'description': book.description or '',
            }

    # 3. Construcción del system prompt
    system_prompt = build_assistant_system_prompt(
        username=user.username if hasattr(user, 'username') else 'lector',
        recent_read_titles=read_titles,
        current_book_info=current_book_info,
    )

    # 4. Invocación al proveedor activo
    provider = get_ai_provider()
    ai_response = provider.chat_completion(
        messages=sanitized_messages,
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=800,
    )

    # 5. Fallback asistido en caso de que el proveedor esté offline
    if not ai_response.get("success"):
        suggested_books = Book.objects.all().order_by('-average_rating')[:3]
        fallback_titles = [
            f"**{b.title}** ({b.author.name if b.author else 'Varios'})"
            for b in suggested_books
        ]

        uname = user.username if hasattr(user, 'username') else 'amigo lector'
        fallback_content = (
            f"¡Hola {uname}! Actualmente el motor neuronal de IA ({provider.name}) no se encuentra activo.\n\n"
            f"Mientras se restablece la conexión, te sugerimos estas obras destacadas de nuestra biblioteca:\n"
            + "\n".join([f"- {t}" for t in fallback_titles])
        )
        return {
            "message": {
                "role": "assistant",
                "content": fallback_content,
            },
            "provider": f"{provider.name}-fallback",
            "model": "rule-based",
            "ai_online": False,
        }

    return {
        "message": {
            "role": "assistant",
            "content": ai_response["content"],
        },
        "provider": ai_response.get("provider", provider.name),
        "model": ai_response.get("model", provider.model_chat),
        "ai_online": True,
    }


def get_book_ai_summary(book: Book) -> dict[str, Any]:
    """
    Genera un análisis y síntesis temática del libro vía IA con fallback determinista.

    :param book: Instancia del modelo Book a analizar.
    :return: Diccionario con 'summary' y 'ai_online'.
    """
    author_name = book.author.name if book.author else 'Desconocido'
    prompt = build_book_summary_prompt(
        title=book.title,
        author_name=author_name,
        description=book.description,
    )

    provider = get_ai_provider()
    response = provider.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="Eres un crítico y analista literario experto, conciso y objetivo.",
        temperature=0.5,
        max_tokens=500,
    )

    if response.get("success"):
        return {
            "summary": response["content"],
            "ai_online": True,
            "provider": provider.name,
        }

    # Fallback determinista
    categories_str = ', '.join([c.name for c in book.categories.all()]) or 'Literatura General'
    fallback = (
        f"**Análisis preliminar de '{book.title}'**:\n\n"
        f"- **Género principal**: {categories_str}\n"
        f"- **Sinopsis breve**: {book.description[:250] if book.description else 'Información en catalogación.'}...\n"
        f"- *(Activa o inicia el servicio de IA para el desglose temático completo)*"
    )
    return {
        "summary": fallback,
        "ai_online": False,
        "provider": "rule-based",
    }


def semantic_search_books(query: str, limit: int = 10) -> Any:
    """
    Realiza una búsqueda conceptual y temática en los libros de la base de datos.

    :param query: Texto o concepto a buscar.
    :param limit: Límite de resultados a retornar.
    :return: QuerySet filtrado de libros afines.
    """
    clean_q = query.strip()
    if not clean_q:
        return Book.objects.none()

    # Normalización de acentos para compatibilidad de búsqueda
    def _strip_accents(s: str) -> str:
        accents = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u', 'ñ': 'n'}
        res = s.lower()
        for k, v in accents.items():
            res = res.replace(k, v)
        return res

    # 1. Búsqueda exacta del término completo
    q_cond = (
        Q(title__icontains=clean_q)
        | Q(description__icontains=clean_q)
        | Q(categories__name__icontains=clean_q)
        | Q(author__name__icontains=clean_q)
    )

    # 2. Descomponer en palabras clave significativas (> 2 caracteres)
    stopwords = {'de', 'la', 'el', 'en', 'un', 'una', 'y', 'o', 'los', 'las', 'por', 'para', 'con', 'sobre', 'que'}
    terms = [w for w in clean_q.split() if w.lower() not in stopwords and len(w) >= 3]

    for term in terms:
        q_cond |= (
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(categories__name__icontains=term)
            | Q(author__name__icontains=term)
        )
        norm_term = _strip_accents(term)
        if norm_term != term.lower():
            q_cond |= (
                Q(title__icontains=norm_term)
                | Q(description__icontains=norm_term)
                | Q(categories__name__icontains=norm_term)
                | Q(author__name__icontains=norm_term)
            )

    return Book.objects.filter(q_cond).distinct().order_by('-average_rating')[:limit]

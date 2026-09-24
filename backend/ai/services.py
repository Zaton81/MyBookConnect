"""
Servicios de alto nivel para interacción conversacional, análisis y búsqueda semántica con IA.
Incluye persistencia de presupuesto y observabilidad (AIUsageLog) y blindaje contra inyección.
"""

import logging
import uuid
from typing import Any

from django.db.models import Q

from ai.clients.factory import get_ai_provider
from ai.models import AIUsageLog
from ai.policies import (
    AIRateLimitExceededError,
    check_ai_rate_limit,
    check_ai_rate_limit_detailed,
    detect_prompt_injection,
    sanitize_book_context,
    validate_and_sanitize_chat_messages,
)
from ai.prompts import build_assistant_system_prompt, build_book_summary_prompt
from ai.tools import execute_tool, get_tools_definitions
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
    request_id: str | None = None,
) -> dict[str, Any]:
    """
    Orquesta la conversación con el asistente literario BookAI, aplicando validación
    de políticas, contextualización de lecturas del usuario, auditoría de consumo y fallback.

    :param user: Instancia del usuario autenticado.
    :param raw_messages: Lista de mensajes recibida desde el frontend.
    :param book_id: ID opcional de libro sobre el que se formula la consulta.
    :param request_id: Identificador correlativo de la petición.
    :return: Diccionario con la respuesta del asistente, metadatos y estado de disponibilidad.
    """
    req_id = request_id or str(uuid.uuid4())

    # 0. Verificación de Rate Limiting multinivel (Sección 10.4)
    if not check_ai_rate_limit(user):
        _, window_name, retry_after = check_ai_rate_limit_detailed(user)
        win = window_name or 'minute'
        ttl = retry_after or 60
        raise AIRateLimitExceededError(
            f"Has superado el límite de consultas permitidas ({win}). Por favor, espera antes de reintentar.",
            window=win,
            retry_after=ttl,
        )

    # 1. Validación y sanitización estricta del historial
    sanitized_messages = validate_and_sanitize_chat_messages(raw_messages)

    # 1.1 Detección defensiva de inyección en el último mensaje de usuario
    for msg in reversed(sanitized_messages):
        if msg['role'] == 'user':
            if detect_prompt_injection(msg['content']):
                logger.warning(
                    "Intento de prompt injection detectado para usuario %s",
                    getattr(user, 'username', 'anon'),
                )
                msg['content'] = f"[Aviso: Directiva insegura neutralizada]: {msg['content']}"
            break

    # 2. Recopilación de contexto de biblioteca del usuario
    read_titles: list[str] = []
    if user and getattr(user, 'is_authenticated', False):
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
                'description': sanitize_book_context(book.description or ''),
            }

    # 3. Construcción del system prompt
    username_str = user.username if (user and hasattr(user, 'username')) else 'lector'
    system_prompt = build_assistant_system_prompt(
        username=username_str,
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

    # 5. Auditoría y registro de presupuesto (Sección 10.5)
    p_tokens = ai_response.get("prompt_tokens", 0)
    c_tokens = ai_response.get("completion_tokens", 0)
    dur_ms = ai_response.get("duration_ms", 0)
    success = ai_response.get("success", False)
    err_msg = ai_response.get("error", "")

    try:
        AIUsageLog.log_usage(
            user=user,
            request_id=req_id,
            provider=ai_response.get("provider", provider.name),
            model=ai_response.get("model", provider.model_chat),
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            duration_ms=dur_ms,
            success=success,
            error=err_msg,
        )
    except Exception as log_exc:
        logger.error("Error al registrar auditoría de IA: %s", log_exc)

    # 6. Fallback asistido en caso de que el proveedor esté offline o falle
    if not success:
        suggested_books = Book.objects.all().order_by('-average_rating')[:3]
        fallback_titles = [
            f"**{b.title}** ({b.author.name if b.author else 'Varios'})"
            for b in suggested_books
        ]

        fallback_content = (
            f"¡Hola {username_str}! Actualmente el motor neuronal de IA ({provider.name}) no se encuentra activo.\n\n"
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
            "request_id": req_id,
        }

    return {
        "message": {
            "role": "assistant",
            "content": ai_response["content"],
        },
        "provider": ai_response.get("provider", provider.name),
        "model": ai_response.get("model", provider.model_chat),
        "ai_online": True,
        "request_id": req_id,
        "usage": {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": ai_response.get("total_tokens", p_tokens + c_tokens),
            "duration_ms": dur_ms,
        },
    }


def get_book_ai_summary(book: Book, request_id: str | None = None) -> dict[str, Any]:
    """
    Genera un análisis y síntesis temática del libro vía IA con fallback determinista y auditoría.

    :param book: Instancia del modelo Book a analizar.
    :param request_id: Identificador correlativo de la petición.
    :return: Diccionario con 'summary', 'ai_online' y metadatos.
    """
    req_id = request_id or str(uuid.uuid4())
    author_name = book.author.name if book.author else 'Desconocido'
    clean_desc = sanitize_book_context(book.description or '')

    prompt = build_book_summary_prompt(
        title=book.title,
        author_name=author_name,
        description=clean_desc,
    )

    provider = get_ai_provider()
    response = provider.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        system_prompt="Eres un crítico y analista literario experto, conciso y objetivo.",
        temperature=0.5,
        max_tokens=500,
    )

    p_tokens = response.get("prompt_tokens", 0)
    c_tokens = response.get("completion_tokens", 0)
    dur_ms = response.get("duration_ms", 0)
    success = response.get("success", False)

    try:
        AIUsageLog.log_usage(
            user=None,
            request_id=req_id,
            provider=response.get("provider", provider.name),
            model=response.get("model", provider.model_chat),
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            duration_ms=dur_ms,
            success=success,
            error=response.get("error", ""),
        )
    except Exception as log_exc:
        logger.error("Error al registrar auditoría de resumen de IA: %s", log_exc)

    if success:
        return {
            "summary": response["content"],
            "ai_online": True,
            "provider": provider.name,
            "request_id": req_id,
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
        "request_id": req_id,
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


def execute_assistant_tool(
    user: Any,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Despacha la ejecución segura de una herramienta solicitada por el asistente de IA
    validando permisos y límites en el backend.

    :param user: Instancia del usuario autenticado.
    :param tool_name: Nombre de la herramienta a invocar (ej: 'catalog_search').
    :param arguments: Argumentos validados para la herramienta.
    :return: Resultado estructurado de la ejecución.
    """
    return execute_tool(name=tool_name, user=user, arguments=arguments)


def get_available_assistant_tools() -> list[dict[str, Any]]:
    """
    Retorna la lista de definiciones de herramientas disponibles en formato OpenAI Tools.

    :return: Lista de esquemas JSON de las herramientas registradas.
    """
    return get_tools_definitions()

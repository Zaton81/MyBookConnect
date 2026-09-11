"""
Paquete modular de Inteligencia Artificial para MyBookConnect (Fase 26).

Proporciona soporte multi-proveedor (OpenAI, Ollama, OpenRouter), cálculo de embeddings,
políticas de seguridad y servicios conversacionales literarios.
"""

from ai.clients import (
    AIProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenRouterProvider,
    get_ai_provider,
)
from ai.config import AISettings, get_ai_settings
from ai.embeddings import (
    cosine_similarity,
    get_embedding_for_text,
    rank_items_by_semantic_similarity,
)
from ai.policies import (
    AIPolicyViolationError,
    validate_and_sanitize_chat_messages,
)
from ai.prompts import (
    build_assistant_system_prompt,
    build_book_summary_prompt,
)
from ai.services import (
    get_ai_status,
    get_assistant_reply,
    get_book_ai_summary,
    semantic_search_books,
)

__all__ = [
    # Proveedores y factoría
    'AIProvider',
    'get_ai_provider',
    'OllamaProvider',
    'OpenAIProvider',
    'OpenRouterProvider',
    # Configuración
    'AISettings',
    'get_ai_settings',
    # Embeddings
    'get_embedding_for_text',
    'cosine_similarity',
    'rank_items_by_semantic_similarity',
    # Políticas
    'AIPolicyViolationError',
    'validate_and_sanitize_chat_messages',
    # Prompts
    'build_assistant_system_prompt',
    'build_book_summary_prompt',
    # Servicios
    'get_ai_status',
    'get_assistant_reply',
    'get_book_ai_summary',
    'semantic_search_books',
]

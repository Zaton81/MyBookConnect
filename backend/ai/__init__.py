"""
Paquete modular de Inteligencia Artificial para MyBookConnect (Fases 26 y 27).

Proporciona soporte multi-proveedor (OpenAI, Ollama, OpenRouter), cálculo de embeddings,
políticas de seguridad, mitigación de prompt injection, llamadas a herramientas seguras
y servicios conversacionales literarios.
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
    AIRateLimitExceededError,
    check_ai_rate_limit,
    detect_prompt_injection,
    sanitize_untrusted_input,
    validate_and_sanitize_chat_messages,
)
from ai.prompts import (
    build_assistant_system_prompt,
    build_book_summary_prompt,
)
from ai.services import (
    execute_assistant_tool,
    get_ai_status,
    get_assistant_reply,
    get_available_assistant_tools,
    get_book_ai_summary,
    semantic_search_books,
)
from ai.tools import (
    AITool,
    ToolExecutionError,
    ToolPermissionDeniedError,
    execute_tool,
    get_registered_tools,
    get_tools_definitions,
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
    # Políticas y Seguridad
    'AIPolicyViolationError',
    'AIRateLimitExceededError',
    'check_ai_rate_limit',
    'detect_prompt_injection',
    'sanitize_untrusted_input',
    'validate_and_sanitize_chat_messages',
    # Prompts
    'build_assistant_system_prompt',
    'build_book_summary_prompt',
    # Servicios
    'get_ai_status',
    'get_assistant_reply',
    'get_book_ai_summary',
    'semantic_search_books',
    'execute_assistant_tool',
    'get_available_assistant_tools',
    # Herramientas (Tool Calling)
    'AITool',
    'ToolExecutionError',
    'ToolPermissionDeniedError',
    'execute_tool',
    'get_registered_tools',
    'get_tools_definitions',
]

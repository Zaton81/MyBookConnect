"""
Paquete modular de Inteligencia Artificial para MyBookConnect (Fases 26 y 27 / Fase 5).

Proporciona soporte multi-proveedor (OpenAI, Ollama, OpenRouter), cálculo de embeddings,
políticas de seguridad, mitigación de prompt injection, llamadas a herramientas seguras,
auditoría de costes y servicios conversacionales literarios.
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

# Servicios y herramientas se importan de forma perezosa (lazy) para evitar ciclos
# con AppRegistryNotReady durante el arranque de Django apps.populate().
_SERVICES_EXPORTS = {
    'get_ai_status',
    'get_assistant_reply',
    'get_book_ai_summary',
    'semantic_search_books',
    'execute_assistant_tool',
    'get_available_assistant_tools',
}

_TOOLS_EXPORTS = {
    'AITool',
    'ToolExecutionError',
    'ToolPermissionDeniedError',
    'execute_tool',
    'get_registered_tools',
    'get_tools_definitions',
}


def __getattr__(name: str):
    if name in _SERVICES_EXPORTS:
        from ai import services
        return getattr(services, name)
    if name in _TOOLS_EXPORTS:
        from ai import tools
        return getattr(tools, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


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
    # Servicios (lazy)
    'get_ai_status',
    'get_assistant_reply',
    'get_book_ai_summary',
    'semantic_search_books',
    'execute_assistant_tool',
    'get_available_assistant_tools',
    # Herramientas (lazy)
    'AITool',
    'ToolExecutionError',
    'ToolPermissionDeniedError',
    'execute_tool',
    'get_registered_tools',
    'get_tools_definitions',
]

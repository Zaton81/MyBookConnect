"""
Factoría para la instanciación y obtención de proveedores de IA.

Permite seleccionar dinámicamente la implementación adecuada (Ollama, OpenAI, OpenRouter)
en base a la configuración activa o a parámetros explícitos.
"""

import logging

from ai.clients.base import AIProvider
from ai.clients.ollama_client import OllamaProvider
from ai.clients.openai_client import OpenAIProvider
from ai.clients.openrouter_client import OpenRouterProvider
from ai.config import AISettings, get_ai_settings

logger = logging.getLogger(__name__)

# Caché en memoria para reutilizar clientes y sesiones
_PROVIDERS_CACHE: dict[str, AIProvider] = {}


def get_ai_provider(
    provider_name: str | None = None,
    settings: AISettings | None = None,
    force_refresh: bool = False,
) -> AIProvider:
    """
    Retorna la instancia del proveedor de IA solicitado o el configurado por defecto.

    :param provider_name: Nombre del proveedor ('ollama', 'openai', 'openrouter'). Si es None, toma settings.provider.
    :param settings: Configuración de IA opcional; si no se provee, carga get_ai_settings().
    :param force_refresh: Si es True, no reutiliza la instancia en caché y crea una nueva.
    :return: Instancia concreta que implementa AIProvider.
    """
    cfg = settings or get_ai_settings()
    target = (provider_name or cfg.provider or 'ollama').lower().strip()

    cache_key = f"{target}_{cfg.base_url}_{cfg.model_chat}"
    if not force_refresh and cache_key in _PROVIDERS_CACHE:
        return _PROVIDERS_CACHE[cache_key]

    provider: AIProvider
    if target == 'openai':
        provider = OpenAIProvider(cfg)
    elif target == 'openrouter':
        provider = OpenRouterProvider(cfg)
    elif target == 'ollama':
        provider = OllamaProvider(cfg)
    else:
        logger.warning(
            "Proveedor de IA '%s' desconocido. Utilizando OllamaProvider como alternativa predeterminada.",
            target,
        )
        provider = OllamaProvider(cfg)

    _PROVIDERS_CACHE[cache_key] = provider
    return provider

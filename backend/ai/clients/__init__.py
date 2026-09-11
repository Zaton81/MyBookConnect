"""
Paquete de clientes de proveedores de Inteligencia Artificial para MyBookConnect.
"""

from ai.clients.base import AIProvider
from ai.clients.factory import get_ai_provider
from ai.clients.ollama_client import OllamaProvider
from ai.clients.openai_client import OpenAIProvider
from ai.clients.openrouter_client import OpenRouterProvider

__all__ = [
    'AIProvider',
    'get_ai_provider',
    'OllamaProvider',
    'OpenAIProvider',
    'OpenRouterProvider',
]

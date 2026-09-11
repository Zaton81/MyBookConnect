"""
Clase base abstracta para proveedores de Inteligencia Artificial (AIProvider).

Establece el contrato que deben implementar todos los clientes de IA
(OpenAI, Ollama, OpenRouter, etc.).
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """
    Interfaz abstracta para proveedores de Inteligencia Artificial.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre distintivo del proveedor (ej: 'ollama', 'openai', 'openrouter')."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL base de la API del proveedor."""
        pass

    @property
    @abstractmethod
    def model_chat(self) -> str:
        """Identificador del modelo de lenguaje utilizado para chat."""
        pass

    @property
    @abstractmethod
    def model_embeddings(self) -> str:
        """Identificador del modelo utilizado para vectores de embeddings."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Indica si el proveedor está habilitado en la configuración."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Verifica la disponibilidad en tiempo real del servicio o endpoint del modelo.

        :return: True si el servicio responde con éxito, False en caso contrario.
        """
        pass

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        """
        Envía una secuencia de mensajes para obtener una respuesta generativa del modelo.

        :param messages: Lista de diccionarios con formato [{'role': 'user', 'content': '...'}].
        :param system_prompt: Instrucción de sistema contextual opcional.
        :param temperature: Parámetro de creatividad / variabilidad (0.0 a 1.0).
        :param max_tokens: Límite máximo de tokens generados en la respuesta.
        :return: Diccionario con campos 'success', 'content', 'provider', 'model' y 'error' (opcional).
        """
        pass

    @abstractmethod
    def get_embedding(self, text: str) -> list[float] | None:
        """
        Genera el vector de representación semántica (embeddings) para el texto proporcionado.

        :param text: Cadena de texto a vectorizar.
        :return: Lista de números flotantes o None en caso de fallo.
        """
        pass

"""
Módulo de compatibilidad para el servicio de IA de MyBookConnect.

Redirige las llamadas al paquete modular `ai` introducido en la Fase 26.
"""

from typing import Any

from ai.clients.factory import get_ai_provider


class OpenAICompatibleClient:
    """
    Proxy de compatibilidad hacia el nuevo subsistema modular de proveedores de IA.
    """

    @property
    def _provider(self):
        return get_ai_provider()

    @property
    def enabled(self) -> bool:
        return self._provider.enabled

    @property
    def base_url(self) -> str:
        return self._provider.base_url

    @property
    def api_key(self) -> str:
        return getattr(self._provider, '_settings', None).api_key if hasattr(self._provider, '_settings') else ''

    @property
    def model_chat(self) -> str:
        return self._provider.model_chat

    @property
    def model_embeddings(self) -> str:
        return self._provider.model_embeddings

    @property
    def timeout(self) -> int:
        return getattr(self._provider, 'timeout', 15)

    def is_available(self) -> bool:
        return self._provider.is_available()

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        return self._provider.chat_completion(
            messages=messages,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def get_embedding(self, text: str) -> list[float] | None:
        return self._provider.get_embedding(text)


# Instancia singleton para compatibilidad con código existente
ai_client = OpenAICompatibleClient()

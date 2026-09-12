"""
Cliente de proveedor para OpenRouter (AIProvider).

Permite acceder a múltiples modelos abiertos y propietarios a través de la pasarela
universal de OpenRouter (https://openrouter.ai/api/v1).
"""

import logging
from typing import Any

import requests

from ai.clients.base import AIProvider
from ai.config import AISettings

logger = logging.getLogger(__name__)


class OpenRouterProvider(AIProvider):
    """
    Proveedor para OpenRouter API.
    """

    DEFAULT_BASE_URL = 'https://openrouter.ai/api/v1'

    def __init__(self, settings: AISettings) -> None:
        """
        Inicializa el cliente de OpenRouter.

        :param settings: Configuración inmutable de IA.
        """
        self._settings = settings
        base = settings.base_url.rstrip('/')
        if 'localhost' in base or '127.0.0.1' in base:
            self._base_url = self.DEFAULT_BASE_URL
        else:
            self._base_url = base

    @property
    def name(self) -> str:
        return 'openrouter'

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model_chat(self) -> str:
        m = self._settings.model_chat
        return 'meta-llama/llama-3.2-3b-instruct:free' if ('llama3.2' == m or not m) else m

    @property
    def model_embeddings(self) -> str:
        return self._settings.model_embeddings or 'openai/text-embedding-3-small'

    @property
    def enabled(self) -> bool:
        return self._settings.enabled and bool(self._settings.api_key and self._settings.api_key != 'ollama')

    @property
    def timeout(self) -> int:
        return self._settings.timeout

    def _get_headers(self) -> dict[str, str]:
        """Genera las cabeceras requeridas por OpenRouter."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self._settings.api_key}",
            'HTTP-Referer': 'https://mybookconnect.local',
            'X-Title': 'MyBookConnect BookAI',
        }

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            res = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=min(self.timeout, 4),
            )
            return res.status_code == 200
        except Exception:
            return False

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> dict[str, Any]:
        if not self.enabled:
            return {
                "success": False,
                "content": "La API de OpenRouter no está configurada o carece de una clave válida.",
                "provider": self.name,
                "model": "offline",
            }

        full_messages: list[dict[str, Any]] = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        payload = {
            "model": self.model_chat,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")
                return {
                    "success": True,
                    "content": content,
                    "provider": self.name,
                    "model": self.model_chat,
                }
            else:
                logger.warning(
                    "OpenRouter retornó código %s: %s",
                    response.status_code,
                    response.text[:200],
                )
                return {
                    "success": False,
                    "content": f"El servicio de OpenRouter respondió con error ({response.status_code}).",
                    "provider": self.name,
                    "model": self.model_chat,
                }
        except requests.exceptions.Timeout:
            logger.warning("Timeout al conectar con OpenRouter tras %ss", self.timeout)
            return {
                "success": False,
                "content": "Tiempo de espera agotado al consultar OpenRouter.",
                "provider": self.name,
                "model": self.model_chat,
            }
        except Exception as exc:
            logger.warning("Error de conexión con OpenRouter: %s", exc)
            return {
                "success": False,
                "content": "No se pudo establecer conexión con OpenRouter.",
                "provider": self.name,
                "model": self.model_chat,
                "error": str(exc),
            }

    def get_embedding(self, text: str) -> list[float] | None:
        if not self.enabled or not text:
            return None

        payload = {
            "model": self.model_embeddings,
            "input": text,
        }

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code == 200:
                data = response.json()
                embedding_data = data.get("data", [{}])[0]
                return embedding_data.get("embedding")
            return None
        except Exception as exc:
            logger.warning("Fallo al obtener embeddings de OpenRouter: %s", exc)
            return None

"""
Cliente de proveedor para OpenAI oficial (AIProvider).

Permite interactuar con modelos de OpenAI (gpt-4o, gpt-4o-mini, text-embedding-3-small, etc.)
mediante su API REST estándar.
"""

import logging
from typing import Any

import requests

from ai.clients.base import AIProvider
from ai.config import AISettings

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """
    Proveedor para la API oficial de OpenAI.
    """

    DEFAULT_BASE_URL = 'https://api.openai.com/v1'

    def __init__(self, settings: AISettings) -> None:
        """
        Inicializa el cliente de OpenAI.

        :param settings: Configuración inmutable de IA.
        """
        self._settings = settings
        # Si la URL configurada es la de Ollama por defecto, usar la oficial de OpenAI
        base = settings.base_url.rstrip('/')
        if 'localhost' in base or '127.0.0.1' in base:
            self._base_url = self.DEFAULT_BASE_URL
        else:
            self._base_url = base

    @property
    def name(self) -> str:
        return 'openai'

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model_chat(self) -> str:
        # Si el modelo configurado es llama, asignar gpt-4o-mini por defecto para OpenAI
        m = self._settings.model_chat
        return 'gpt-4o-mini' if ('llama' in m or not m) else m

    @property
    def model_embeddings(self) -> str:
        m = self._settings.model_embeddings
        return 'text-embedding-3-small' if ('nomic' in m or not m) else m

    @property
    def enabled(self) -> bool:
        return self._settings.enabled and bool(self._settings.api_key and self._settings.api_key != 'ollama')

    @property
    def timeout(self) -> int:
        return self._settings.timeout

    def _get_headers(self) -> dict[str, str]:
        """Genera las cabeceras HTTP de autenticación con Bearer token de OpenAI."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self._settings.api_key}",
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
                "content": "La API de OpenAI no está configurada o carece de una clave válida.",
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
                    "OpenAI retornó código %s: %s",
                    response.status_code,
                    response.text[:200],
                )
                return {
                    "success": False,
                    "content": f"El servicio de OpenAI respondió con error ({response.status_code}).",
                    "provider": self.name,
                    "model": self.model_chat,
                }
        except requests.exceptions.Timeout:
            logger.warning("Timeout al conectar con OpenAI tras %ss", self.timeout)
            return {
                "success": False,
                "content": "Tiempo de espera agotado al consultar OpenAI.",
                "provider": self.name,
                "model": self.model_chat,
            }
        except Exception as exc:
            logger.warning("Error de conexión con OpenAI: %s", exc)
            return {
                "success": False,
                "content": "No se pudo establecer conexión con OpenAI.",
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
            logger.warning("Fallo al obtener embeddings de OpenAI: %s", exc)
            return None

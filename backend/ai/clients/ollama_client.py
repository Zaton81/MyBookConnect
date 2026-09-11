"""
Cliente de proveedor para Ollama (AIProvider).

Permite interactuar con modelos locales de código abierto (Llama 3, Mistral,
Nomic-Embed, etc.) a través de su endpoint compatible con OpenAI.
"""

import logging
from typing import Any

import requests

from ai.clients.base import AIProvider
from ai.config import AISettings

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """
    Proveedor para instancias locales o remotas de Ollama.
    """

    def __init__(self, settings: AISettings) -> None:
        """
        Inicializa el cliente de Ollama con los parámetros provistos.

        :param settings: Configuración inmutable de IA.
        """
        self._settings = settings
        # Si la URL no especifica versión, asegurar /v1 para compatibilidad OpenAI
        base = settings.base_url.rstrip('/')
        if not base.endswith('/v1'):
            base = f"{base}/v1"
        self._base_url = base

    @property
    def name(self) -> str:
        return 'ollama'

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model_chat(self) -> str:
        return self._settings.model_chat or 'llama3.2'

    @property
    def model_embeddings(self) -> str:
        return self._settings.model_embeddings or 'nomic-embed-text'

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @property
    def timeout(self) -> int:
        return self._settings.timeout

    def _get_headers(self) -> dict[str, str]:
        """Genera las cabeceras HTTP necesarias para las peticiones a Ollama."""
        headers = {'Content-Type': 'application/json'}
        if self._settings.api_key:
            headers['Authorization'] = f"Bearer {self._settings.api_key}"
        return headers

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            res = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=min(self.timeout, 3),
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
                "content": "El servicio de Inteligencia Artificial está desactivado.",
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
                    "Ollama retornó código %s: %s",
                    response.status_code,
                    response.text[:200],
                )
                return {
                    "success": False,
                    "content": f"El servicio local de Ollama respondió con error ({response.status_code}).",
                    "provider": self.name,
                    "model": self.model_chat,
                }
        except requests.exceptions.Timeout:
            logger.warning("Timeout al conectar con Ollama tras %ss", self.timeout)
            return {
                "success": False,
                "content": "Tiempo de espera agotado al consultar el modelo de Ollama.",
                "provider": self.name,
                "model": self.model_chat,
            }
        except Exception as exc:
            logger.warning("Error de conexión con Ollama: %s", exc)
            return {
                "success": False,
                "content": "No se pudo establecer conexión con Ollama en este momento.",
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
            logger.warning("Fallo al obtener embeddings de Ollama: %s", exc)
            return None

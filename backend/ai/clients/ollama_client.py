"""
Cliente de proveedor para Ollama local (AIProvider).

Permite interactuar con modelos ejecutados localmente mediante Ollama
(Llama 3.2, Mistral, Gemma, nomic-embed-text) a través de su endpoint compatible con OpenAI.
"""

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from ai.clients.base import AIProvider
from ai.config import AISettings

logger = logging.getLogger(__name__)


class OllamaProvider(AIProvider):
    """
    Proveedor para Ollama local con soporte de resiliencia y métricas de tokens.
    """

    def __init__(self, settings: AISettings) -> None:
        """
        Inicializa el cliente de Ollama configurando sesión HTTP resiliente.

        :param settings: Configuración inmutable de IA.
        """
        self._settings = settings
        self._base_url = settings.base_url.rstrip('/')

        # Sesión HTTP reutilizable con retries y backoff exponencial (Sección 10.3)
        self._session = requests.Session()
        retries = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self._session.mount('https://', adapter)
        self._session.mount('http://', adapter)

    @property
    def name(self) -> str:
        return 'ollama'

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def model_chat(self) -> str:
        return self._settings.model_chat

    @property
    def model_embeddings(self) -> str:
        return self._settings.model_embeddings

    @property
    def enabled(self) -> bool:
        return self._settings.enabled

    @property
    def timeout(self) -> int:
        return self._settings.timeout

    def _get_headers(self) -> dict[str, str]:
        """Genera las cabeceras HTTP necesarias para el endpoint de Ollama."""
        return {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self._settings.api_key}",
        }

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            res = self._session.get(
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
                "content": "El servicio de Inteligencia Artificial está desactivado.",
                "provider": self.name,
                "model": "offline",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "duration_ms": 0,
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

        start_time = time.perf_counter()
        try:
            response = self._session.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout,
            )
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                choice = data.get("choices", [{}])[0]
                content = choice.get("message", {}).get("content", "")

                # Extraer usage desde formato OpenAI v1 o nativo Ollama
                usage = data.get("usage", {})
                p_tokens = usage.get("prompt_tokens", data.get("prompt_eval_count", 0))
                c_tokens = usage.get("completion_tokens", data.get("eval_count", 0))
                t_tokens = usage.get("total_tokens", p_tokens + c_tokens)

                return {
                    "success": True,
                    "content": content,
                    "provider": self.name,
                    "model": self.model_chat,
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": t_tokens,
                    "duration_ms": duration_ms,
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
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "duration_ms": duration_ms,
                    "error": f"HTTP {response.status_code}",
                }
        except requests.exceptions.Timeout:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning("Timeout al conectar con Ollama tras %ss", self.timeout)
            return {
                "success": False,
                "content": "Tiempo de espera agotado al consultar el modelo de Ollama.",
                "provider": self.name,
                "model": self.model_chat,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "duration_ms": duration_ms,
                "error": "Timeout",
            }
        except Exception as exc:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning("Error de conexión con Ollama: %s", exc)
            return {
                "success": False,
                "content": "No se pudo establecer conexión con el servidor local de Ollama.",
                "provider": self.name,
                "model": self.model_chat,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "duration_ms": duration_ms,
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
            response = self._session.post(
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

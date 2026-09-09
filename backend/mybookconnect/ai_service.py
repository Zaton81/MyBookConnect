import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    """
    Cliente agnóstico a proveedores compatible con la especificación de API de OpenAI.
    Funciona de forma transparente con:
    - Ollama en local (http://localhost:11434/v1)
    - LM Studio / vLLM / LocalAI
    - OpenAI, Groq, Mistral, DeepSeek, OpenRouter
    """

    @property
    def enabled(self) -> bool:
        return getattr(settings, 'AI_ENABLED', True)

    @property
    def base_url(self) -> str:
        return getattr(settings, 'AI_API_BASE_URL', 'http://localhost:11434/v1').rstrip('/')

    @property
    def api_key(self) -> str:
        return getattr(settings, 'AI_API_KEY', 'ollama')

    @property
    def model_chat(self) -> str:
        return getattr(settings, 'AI_MODEL_CHAT', 'llama3.2')

    @property
    def model_embeddings(self) -> str:
        return getattr(settings, 'AI_MODEL_EMBEDDINGS', 'nomic-embed-text')

    @property
    def timeout(self) -> int:
        return getattr(settings, 'AI_TIMEOUT', 15)

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            res = requests.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=3,
            )
            return res.status_code == 200
        except Exception:
            return False

    def _get_headers(self) -> dict:
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        return headers

    def chat_completion(
        self,
        messages: list[dict],
        system_prompt: str = None,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> dict:
        """
        Envía un prompt a la API de completions compatible con OpenAI.
        Si el servicio no responde, ejecuta un fallback algorítmico sin lanzar excepción 500.
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        if not self.enabled:
            return {
                "success": False,
                "content": "El servicio de Inteligencia Artificial está desactivado en la configuración.",
                "provider": "local-fallback",
                "model": "offline",
            }

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
                    "provider": self.base_url,
                    "model": self.model_chat,
                }
            else:
                logger.warning(
                    f"AI provider returned status {response.status_code}: {response.text[:200]}"
                )
                return {
                    "success": False,
                    "content": f"El proveedor de IA respondió con error ({response.status_code}).",
                    "provider": self.base_url,
                    "model": self.model_chat,
                }
        except requests.exceptions.Timeout:
            logger.warning(f"AI provider timed out after {self.timeout}s.")
            return {
                "success": False,
                "content": "Tiempo de espera agotado al consultar el modelo de IA.",
                "provider": self.base_url,
                "model": self.model_chat,
            }
        except Exception as e:
            logger.warning(f"AI provider connection unavailable: {e}")
            return {
                "success": False,
                "content": "No se pudo establecer conexión con el proveedor de IA.",
                "provider": self.base_url,
                "model": self.model_chat,
                "error": str(e),
            }

    def get_embedding(self, text: str) -> list[float] | None:
        """
        Calcula el vector de embeddings para el texto dado.
        """
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
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return None


# Singleton global para reutilización de conexiones
ai_client = OpenAICompatibleClient()

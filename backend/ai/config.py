"""
Módulo de configuración centralizada para el subsistema de Inteligencia Artificial.

Expone parámetros configurables para proveedores, modelos de chat y embeddings,
tiempos límite y endpoints compatibles con OpenAI.
"""

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class AISettings:
    """
    Representa la configuración inmutable del motor de IA.
    """
    enabled: bool
    provider: str
    base_url: str
    api_key: str
    model_chat: str
    model_embeddings: str
    timeout: int

    @classmethod
    def from_django_settings(cls) -> 'AISettings':
        """
        Carga la configuración activa a partir de los ajustes de Django.

        :return: Instancia inmutable de AISettings.
        """
        return cls(
            enabled=getattr(settings, 'AI_ENABLED', True),
            provider=getattr(settings, 'AI_PROVIDER', 'ollama').lower().strip(),
            base_url=getattr(settings, 'AI_API_BASE_URL', 'http://localhost:11434/v1').rstrip('/'),
            api_key=getattr(settings, 'AI_API_KEY', 'ollama'),
            model_chat=getattr(settings, 'AI_MODEL', getattr(settings, 'AI_MODEL_CHAT', 'llama3.2')),
            model_embeddings=getattr(
                settings,
                'AI_EMBEDDING_MODEL',
                getattr(settings, 'AI_MODEL_EMBEDDINGS', 'nomic-embed-text'),
            ),
            timeout=getattr(settings, 'AI_TIMEOUT', 15),
        )


def get_ai_settings() -> AISettings:
    """
    Retorna la configuración actual del subsistema de Inteligencia Artificial.

    :return: Instancia de AISettings con los valores vigentes.
    """
    return AISettings.from_django_settings()

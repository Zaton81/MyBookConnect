"""
Políticas de seguridad, validación de mensajes y límites para el asistente de IA (Fase 5 - RoadmapV2).

Protege la aplicación contra:
- Sobrecarga de contexto y consumo descontrolado de tokens.
- Inyecciones de prompts (prompt injection / jailbreaks).
- Inyección de roles no autorizados (system, developer, tool).
- Parámetros de control reservados para el backend (provider, model, temperature, max_tokens, etc.).
- Abuso y denegación de servicio mediante Rate Limiting multinivel en Redis (minuto, hora, día).
"""

import re
from typing import Any

from django.conf import settings
from django.core.cache import cache

MAX_MESSAGES_COUNT = 20
MAX_MESSAGE_LENGTH = 3000
MAX_TOTAL_MESSAGES_LENGTH = 12000
ALLOWED_ROLES = {'user', 'assistant'}

# Parámetros que el cliente jamás puede manipular directamente (Sección 10.2 RoadmapV2)
FORBIDDEN_CLIENT_PARAMS = {
    'system',
    'system_prompt',
    'tools',
    'provider',
    'model',
    'temperature',
    'max_tokens',
    'prompt',
}

# Patrones típicos de evasión, jailbreak y anulación de directivas del sistema
INJECTION_PATTERNS = [
    re.compile(r'ignore\s+(all\s+)?(previous|prior)\s+(instructions|directives|rules)', re.IGNORECASE),
    re.compile(r'disregard\s+(all\s+)?(previous|prior)\s+(instructions|rules)', re.IGNORECASE),
    re.compile(r'olvida\s+(todas\s+las\s+)?(instrucciones|reglas|directivas)\s+(anteriores|previas)', re.IGNORECASE),
    re.compile(r'system\s*override', re.IGNORECASE),
    re.compile(r'you\s+are\s+now\s+(an\s+unfiltered|dan\b|free\s+of\s+rules)', re.IGNORECASE),
    re.compile(r'act\s+as\s+(an\s+unrestricted|unfiltered\s+ai|dan\b)', re.IGNORECASE),
    re.compile(r'modo\s+dan\b', re.IGNORECASE),
    re.compile(r'nueva\s+regla\s*:', re.IGNORECASE),
    re.compile(r'bypass\s+safety\s+protocols', re.IGNORECASE),
    re.compile(r'<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|<<SYS>>|</SYS>', re.IGNORECASE),
]

# Tokens de control de LLMs que deben ser neutralizados
SPECIAL_LLM_TOKENS = [
    '<|im_start|>',
    '<|im_end|>',
    '<|endoftext|>',
    '[INST]',
    '[/INST]',
    '<<SYS>>',
    '</SYS>',
    '<s>',
    '</s>',
]


class AIPolicyViolationError(ValueError):
    """Excepción lanzada cuando una petición no cumple las políticas de seguridad de IA."""
    pass


class AIRateLimitExceededError(AIPolicyViolationError):
    """Excepción lanzada cuando un usuario supera las cuotas de tasa del asistente de IA."""
    def __init__(self, message: str, window: str = 'minute', retry_after: int = 60) -> None:
        super().__init__(message)
        self.window = window
        self.retry_after = retry_after


def validate_forbidden_client_parameters(data: dict[str, Any]) -> None:
    """
    Verifica que el cuerpo de la petición no contenga parámetros de control del modelo
    o instrucciones reservadas exclusivamente al backend (Sección 10.2).

    :param data: Diccionario de datos de la petición (request.data).
    :raises AIPolicyViolationError: Si se detecta un parámetro reservado o no permitido.
    """
    if not isinstance(data, dict):
        return

    for key in data.keys():
        clean_key = str(key).lower().strip()
        if clean_key in FORBIDDEN_CLIENT_PARAMS:
            raise AIPolicyViolationError(
                f"El parámetro '{key}' no puede ser controlado directamente por el cliente."
            )


def detect_prompt_injection(text: str) -> bool:
    """
    Analiza heurísticamente si una cadena de texto contiene patrones de inyección de prompts,
    intentos de sobrescribir instrucciones de sistema o jailbreaks conocidos.

    :param text: Texto a evaluar.
    :return: True si se detecta un patrón sospechoso, False en caso contrario.
    """
    if not text:
        return False

    clean_text = text.strip()
    for pattern in INJECTION_PATTERNS:
        if pattern.search(clean_text):
            return True
    return False


def sanitize_untrusted_input(text: str) -> str:
    """
    Sanitiza entradas dinámicas de usuarios y fuentes no confiables (reseñas, comentarios,
    descripciones externas), neutralizando tokens especiales de LLMs y caracteres de control.

    :param text: Texto de entrada.
    :return: Texto sanitizado seguro para ser inyectado en el contexto del modelo.
    """
    if not text:
        return ''

    # 1. Eliminar caracteres de control nulos o no imprimibles (excepto saltos de línea y tabuladores)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', str(text))

    # 2. Neutralizar tokens especiales de formateo de instrucciones LLM
    for token in SPECIAL_LLM_TOKENS:
        if token in sanitized:
            sanitized = sanitized.replace(token, f"[neutralized:{token.strip('<>|[]')}]")

    return sanitized.strip()


def sanitize_book_context(text: str, max_chars: int = 2000) -> str:
    """
    Sanitiza descripciones y metadatos de libros antes de agregarlos al prompt del sistema,
    garantizando que ninguna instrucción maliciosa en sinopsis sea interpretada como comando (Sección 10.6).

    :param text: Descripción o sinopsis del libro.
    :param max_chars: Longitud máxima permitida para acotar el contexto.
    :return: Texto desarmado e inocuo para el LLM.
    """
    if not text:
        return ''

    clean = sanitize_untrusted_input(text)

    # Neutralizar intentos de inyección pasiva en libros/documentos
    for pattern in INJECTION_PATTERNS:
        clean = pattern.sub('[contenido neutralizado]', clean)

    if len(clean) > max_chars:
        clean = clean[:max_chars] + '...'

    return clean.strip()


def check_ai_rate_limit(
    user: Any,
    limit: int | None = None,
    window_seconds: int | None = None,
) -> bool:
    """
    Aplica política de Rate Limiting multinivel (Minuto, Hora, Día) en Redis.
    Si se especifican 'limit' y 'window_seconds', evalúa esa ventana puntual (retrocompatibilidad).
    De lo contrario, evalúa concurrentemente las 3 ventanas configuradas en settings.

    :param user: Instancia del usuario autenticado.
    :param limit: Límite específico opcional.
    :param window_seconds: Segundos específicos opcionales.
    :return: True si está dentro de todos los límites, False si excedió alguna cuota.
    """
    user_id = getattr(user, 'id', None)
    if not user_id:
        return True

    # Caso ventana única parametrizada
    if limit is not None and window_seconds is not None:
        cache_key = f"ai:ratelimit:user:{user_id}:custom_{window_seconds}"
        try:
            is_new = cache.add(cache_key, 1, timeout=window_seconds)
            if not is_new:
                count = cache.incr(cache_key)
                if count > limit:
                    return False
            return True
        except Exception:
            return True

    # Ventanas por defecto (Sección 10.4)
    windows = [
        ('minute', getattr(settings, 'AI_RATE_LIMIT_PER_MINUTE', 20), 60),
        ('hour', getattr(settings, 'AI_RATE_LIMIT_PER_HOUR', 100), 3600),
        ('day', getattr(settings, 'AI_RATE_LIMIT_PER_DAY', 500), 86400),
    ]

    try:
        for window_name, max_reqs, ttl in windows:
            key = f"ai:ratelimit:user:{user_id}:{window_name}"
            is_new = cache.add(key, 1, timeout=ttl)
            if not is_new:
                current_count = cache.incr(key)
                if current_count > max_reqs:
                    return False
        return True
    except Exception:
        # Falla abierta defensiva de caché para evitar denegación de servicio accidental si Redis falla
        return True


def check_ai_rate_limit_detailed(user: Any) -> tuple[bool, str, int]:
    """
    Evalúa detalladamente las cuotas de tasa e informa qué ventana exacta fue superada
    junto al tiempo sugerido de espera (Retry-After).

    :return: Tupla (is_allowed, exceeded_window_name, retry_after_seconds)
    """
    user_id = getattr(user, 'id', None)
    if not user_id:
        return True, '', 0

    windows = [
        ('minute', getattr(settings, 'AI_RATE_LIMIT_PER_MINUTE', 20), 60),
        ('hour', getattr(settings, 'AI_RATE_LIMIT_PER_HOUR', 100), 3600),
        ('day', getattr(settings, 'AI_RATE_LIMIT_PER_DAY', 500), 86400),
    ]

    try:
        for window_name, max_reqs, ttl in windows:
            key = f"ai:ratelimit:user:{user_id}:{window_name}"
            is_new = cache.add(key, 1, timeout=ttl)
            if not is_new:
                current_count = cache.incr(key)
                if current_count > max_reqs:
                    return False, window_name, ttl
        return True, '', 0
    except Exception:
        return True, '', 0


def validate_and_sanitize_chat_messages(raw_messages: Any) -> list[dict[str, str]]:
    """
    Valida y sanitiza exhaustivamente la lista de mensajes recibida del cliente.

    Reglas aplicadas:
    1. Debe ser una lista no vacía.
    2. Longitud máxima acotada a MAX_MESSAGES_COUNT (conservando los más recientes).
    3. Cada mensaje debe contener claves 'role' y 'content'.
    4. El rol debe pertenecer a ALLOWED_ROLES ('user' o 'assistant'). No se permite inyectar 'system'.
    5. El contenido no puede estar vacío y se acota a MAX_MESSAGE_LENGTH caracteres.
    6. Se neutralizan tokens de control de LLM en cada mensaje.
    7. La longitud acumulada total de todos los mensajes no puede exceder MAX_TOTAL_MESSAGES_LENGTH.

    :param raw_messages: Objeto recibido en la petición (payload JSON).
    :return: Lista de mensajes sanitizados listos para enviar al modelo.
    :raises AIPolicyViolationError: Si la estructura no es válida o viola las restricciones.
    """
    if not isinstance(raw_messages, list) or not raw_messages:
        raise AIPolicyViolationError(
            "Se requiere una lista no vacía de mensajes con formato [{'role': 'user', 'content': '...'}]"
        )

    # Conservar los últimos N mensajes si excede el límite
    trimmed_messages = raw_messages[-MAX_MESSAGES_COUNT:]
    sanitized: list[dict[str, str]] = []
    total_length = 0

    for idx, msg in enumerate(trimmed_messages):
        if not isinstance(msg, dict):
            raise AIPolicyViolationError(f"El elemento en el índice {idx} debe ser un objeto JSON.")

        role = str(msg.get('role', '')).lower().strip()
        if role not in ALLOWED_ROLES:
            raise AIPolicyViolationError(
                f"Rol '{role}' no permitido. Únicamente se aceptan los roles 'user' y 'assistant'."
            )

        raw_content = str(msg.get('content', '')).strip()
        if not raw_content:
            raise AIPolicyViolationError("El contenido de cada mensaje no puede estar vacío.")

        # Sanitizar tokens de control y caracteres peligrosos
        clean_content = sanitize_untrusted_input(raw_content)

        # Truncamiento defensivo individual
        if len(clean_content) > MAX_MESSAGE_LENGTH:
            clean_content = clean_content[:MAX_MESSAGE_LENGTH]

        total_length += len(clean_content)
        sanitized.append({
            'role': role,
            'content': clean_content,
        })

    # Si la longitud acumulada supera el límite de seguridad, podar mensajes antiguos
    while total_length > MAX_TOTAL_MESSAGES_LENGTH and len(sanitized) > 1:
        removed = sanitized.pop(0)
        total_length -= len(removed['content'])

    return sanitized

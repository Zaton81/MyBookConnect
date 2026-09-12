"""
Políticas de seguridad, validación de mensajes y límites para el asistente de IA (Fase 27).

Protege la aplicación contra sobrecarga de contexto, inyecciones de prompts (prompt injection / jailbreaks),
inyección de roles de sistema no autorizados y abuso mediante rate limiting.
"""

import re
from typing import Any

from django.core.cache import cache

MAX_MESSAGES_COUNT = 20
MAX_MESSAGE_LENGTH = 3000
MAX_TOTAL_MESSAGES_LENGTH = 12000
ALLOWED_ROLES = {'user', 'assistant'}

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
    """Excepción lanzada cuando un usuario supera el límite de peticiones al asistente."""
    pass


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
            # Reemplazar con versión escapada inocua
            sanitized = sanitized.replace(token, f"[neutralized:{token.strip('<>|[]')}]")

    return sanitized.strip()


def check_ai_rate_limit(user: Any, limit: int = 30, window_seconds: int = 60) -> bool:
    """
    Aplica una política de límite de frecuencia (Rate Limiting) por usuario
    utilizando el backend de caché de Redis.

    :param user: Instancia del usuario autenticado.
    :param limit: Número máximo de peticiones permitidas en la ventana.
    :param window_seconds: Duración de la ventana de tiempo en segundos (por defecto 60s).
    :return: True si está dentro del límite permitido, False si superó la cuota.
    """
    user_id = getattr(user, 'id', None)
    if not user_id:
        return True  # Si no hay id identificable, no bloquea por esta vía

    cache_key = f"ai:ratelimit:user:{user_id}"

    try:
        # Añadir con valor inicial 1 si no existe
        is_new = cache.add(cache_key, 1, timeout=window_seconds)
        if not is_new:
            current_count = cache.incr(cache_key)
            if current_count > limit:
                return False
        return True
    except Exception:
        # Si la caché no está disponible, permitir la petición para evitar denegación de servicio accidental
        return True


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

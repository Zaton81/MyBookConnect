"""
Políticas de seguridad, validación de mensajes y límites para el asistente de IA.

Protege la aplicación contra sobrecarga de contexto, inyección de roles de sistema
no autorizados y mensajes malformados.
"""

from typing import Any

MAX_MESSAGES_COUNT = 20
MAX_MESSAGE_LENGTH = 3000
ALLOWED_ROLES = {'user', 'assistant'}


class AIPolicyViolationError(ValueError):
    """Excepción lanzada cuando una petición no cumple las políticas de seguridad de IA."""
    pass


def validate_and_sanitize_chat_messages(raw_messages: Any) -> list[dict[str, str]]:
    """
    Valida y sanitiza la lista de mensajes recibida del cliente.

    Reglas aplicadas:
    1. Debe ser una lista no vacía.
    2. Longitud máxima acotada a MAX_MESSAGES_COUNT (conservando los más recientes).
    3. Cada mensaje debe contener claves 'role' y 'content'.
    4. El rol debe pertenecer a ALLOWED_ROLES ('user' o 'assistant'). No se permite inyectar 'system'.
    5. El contenido debe ser texto no vacío y acotado a MAX_MESSAGE_LENGTH caracteres.

    :param raw_messages: Objeto recibido en la petición (payload JSON).
    :return: Lista de mensajes sanitizados listos para enviar al modelo.
    :raises AIPolicyViolationError: Si la estructura no es válida o viola las restricciones de rol.
    """
    if not isinstance(raw_messages, list) or not raw_messages:
        raise AIPolicyViolationError(
            "Se requiere una lista no vacía de mensajes con formato [{'role': 'user', 'content': '...'}]"
        )

    # Conservar los últimos N mensajes si excede el límite
    trimmed_messages = raw_messages[-MAX_MESSAGES_COUNT:]
    sanitized: list[dict[str, str]] = []

    for idx, msg in enumerate(trimmed_messages):
        if not isinstance(msg, dict):
            raise AIPolicyViolationError(f"El elemento en el índice {idx} debe ser un objeto JSON.")

        role = str(msg.get('role', '')).lower().strip()
        if role not in ALLOWED_ROLES:
            raise AIPolicyViolationError(
                f"Rol '{role}' no permitido. Únicamente se aceptan los roles 'user' y 'assistant'."
            )

        content = str(msg.get('content', '')).strip()
        if not content:
            raise AIPolicyViolationError("El contenido de cada mensaje no puede estar vacío.")

        # Truncamiento defensivo
        if len(content) > MAX_MESSAGE_LENGTH:
            content = content[:MAX_MESSAGE_LENGTH]

        sanitized.append({
            'role': role,
            'content': content,
        })

    return sanitized

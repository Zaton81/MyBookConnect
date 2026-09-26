"""
Formateadores de logging estructurado y utilidades de sanitización para MyBookConnect.
Fase 14 — Observabilidad (RoadmapV2, Sección 19.1).
Produce logs en formato JSON con campos canónicos:
- timestamp
- request_id
- user_id
- method
- path
- status
- duration
Y garantiza la no inclusión de passwords, JWTs, API keys o secretos.
"""
import datetime
import json
import logging
import re
from typing import Any

# Claves sensibles a enmascarar en logs, query params y cuerpos de petición
SENSITIVE_KEY_PATTERNS = re.compile(
    r'(password|passwd|pwd|secret|token|access|refresh|api[_-]?key|auth|authorization|credit[_-]?card|cvv|private[_-]?key)',
    re.IGNORECASE,
)

# Patrón para identificar tokens JWT sueltos (tres segmentos en base64url separados por puntos)
JWT_PATTERN = re.compile(
    r'^eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}$'
)

REDACTED_PLACEHOLDER = '***REDACTED***'


def sanitize_sensitive_data(data: Any) -> Any:
    """
    Sanitiza recursivamente diccionarios, listas o cadenas para enmascarar
    credenciales, contraseñas, tokens JWT, tokens de autenticación o claves de API.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            str_key = str(key)
            if SENSITIVE_KEY_PATTERNS.search(str_key):
                if isinstance(value, str) and value.strip().lower().startswith('bearer '):
                    sanitized[key] = f'Bearer {REDACTED_PLACEHOLDER}'
                else:
                    sanitized[key] = REDACTED_PLACEHOLDER
            else:
                sanitized[key] = sanitize_sensitive_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_sensitive_data(item) for item in data)
    elif isinstance(data, str):
        trimmed = data.strip()
        # Si la cadena parece un Bearer token
        if trimmed.lower().startswith('bearer ') and len(trimmed) > 7:
            return 'Bearer ***REDACTED***'
        # Si la cadena es un token JWT directo
        if JWT_PATTERN.match(trimmed):
            return REDACTED_PLACEHOLDER
        return data
    return data


class StructuredJsonFormatter(logging.Formatter):
    """
    Formateador de logs que produce una salida estructurada en formato JSON
    para integración con sistemas de observabilidad (Datadog, Grafana Loki, CloudWatch, etc.).
    Cumple con el estándar de la Sección 19.1 de RoadmapV2.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Obtenemos mensaje base formateado
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        timestamp_iso = datetime.datetime.fromtimestamp(
            record.created, tz=datetime.timezone.utc
        ).isoformat()

        # Extraer atributos canónicos del registro (con fallback seguro)
        request_id = getattr(record, 'request_id', None) or getattr(record, 'req_id', 'system')
        user_id = getattr(record, 'user_id', None)
        method = getattr(record, 'method', None)
        path = getattr(record, 'path', None) or getattr(record, 'endpoint', None)
        status_code = getattr(record, 'status_code', None) or getattr(record, 'status', None)
        duration_ms = getattr(record, 'duration_ms', None) or getattr(record, 'duration', None)

        log_data = {
            # 7 campos obligatorios Fase 14 (19.1)
            'timestamp': timestamp_iso,
            'request_id': request_id,
            'user_id': user_id,
            'method': method,
            'path': path,
            'status': status_code,
            'duration': duration_ms,
            # Metadatos del runtime y log
            'level': record.levelname,
            'logger': record.name,
            'message': message,
            'module': record.module,
            'funcName': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
        }

        # Campos adicionales de rendimiento y trazabilidad si existen
        for attr in ('status_code', 'duration_ms', 'db_queries', 'db_duration_ms', 'ip', 'endpoint'):
            if hasattr(record, attr) and attr not in log_data:
                log_data[attr] = getattr(record, attr)

        # Capturar traza de excepción si existe
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        elif record.exc_text:
            log_data['exception'] = record.exc_text

        # Extraer otros atributos extra definidos por el usuario en el log
        standard_attrs = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename',
            'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName',
            'created', 'msecs', 'relativeCreated', 'thread', 'threadName',
            'processName', 'process', 'message', 'asctime',
        }
        for key, val in record.__dict__.items():
            if key not in standard_attrs and key not in log_data:
                log_data[key] = val

        # Sanitización estricta de datos sensibles antes de serializar
        sanitized_log_data = sanitize_sensitive_data(log_data)

        try:
            return json.dumps(sanitized_log_data, default=str, ensure_ascii=False)
        except Exception:
            return json.dumps({
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'level': 'ERROR',
                'logger': 'mybookconnect.observability',
                'message': 'Error serializing structured log to JSON',
            })

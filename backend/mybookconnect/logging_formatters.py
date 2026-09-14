"""
Formateadores de logging estructurado y utilidades de sanitización para MyBookConnect.
Este módulo no debe importar modelos de Django ni dependencias de DRF para permitir
que Django configure el sistema de logging antes de cargar el registro de aplicaciones.
"""
import datetime
import json
import logging
import re
from typing import Any

# Claves sensibles a enmascarar en logs y parámetros
SENSITIVE_KEY_PATTERNS = re.compile(
    r'(password|passwd|secret|token|access|refresh|api[_-]?key|auth|authorization|credit[_-]?card)',
    re.IGNORECASE,
)
REDACTED_PLACEHOLDER = '***REDACTED***'


def sanitize_sensitive_data(data: Any) -> Any:
    """
    Sanitiza recursivamente diccionarios, listas o cadenas para enmascarar
    credenciales, tokens de autenticación o claves de API.
    """
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            str_key = str(key)
            if SENSITIVE_KEY_PATTERNS.search(str_key):
                sanitized[key] = REDACTED_PLACEHOLDER
            else:
                sanitized[key] = sanitize_sensitive_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sensitive_data(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(sanitize_sensitive_data(item) for item in data)
    elif isinstance(data, str):
        # Si la cadena parece un Bearer token o similar
        if data.strip().lower().startswith('bearer ') and len(data.strip()) > 10:
            return 'Bearer ***REDACTED***'
        return data
    return data


class StructuredJsonFormatter(logging.Formatter):
    """
    Formateador de logs que produce una salida estructurada en formato JSON
    para integración con sistemas de observabilidad (Datadog, Grafana Loki, CloudWatch, etc.).
    Garantiza que ninguna credencial, token o contraseña sensible quede expuesta.
    """
    def format(self, record: logging.LogRecord) -> str:
        # Obtenemos mensaje base formateado
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)

        log_data = {
            'timestamp': datetime.datetime.fromtimestamp(
                record.created, tz=datetime.timezone.utc
            ).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': message,
            'module': record.module,
            'funcName': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread,
        }

        # Extraer campos de contexto HTTP / trazabilidad si existen
        for attr in ('request_id', 'method', 'path', 'status_code', 'duration_ms', 'db_queries', 'user_id', 'ip'):
            if hasattr(record, attr):
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

        # Sanitización de datos sensibles antes de serializar
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

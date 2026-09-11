"""
Utilidades centralizadas para resolución de URLs de archivos multimedia.
Garantiza portabilidad entre entornos locales y producción sin URLs 'hardcodeadas'.
"""
import os
from django.conf import settings


def build_media_url(file_field_or_url, request=None) -> str | None:
    """
    Devuelve la URL pública y accesible para un archivo multimedia.

    Resolución:
    1. Si es None o vacío, retorna None.
    2. Si ya es una URL absoluta ('http://...' o 'https://...'), se retorna tal cual.
    3. Si MEDIA_BASE_URL está configurado en settings (o env), se prefija a la ruta relativa.
    4. Si hay un objeto `request` de Django disponible, usa `request.build_absolute_uri(url)`.
    5. Como fallback final, retorna la ruta relativa normalizada.
    """
    if not file_field_or_url:
        return None

    url = file_field_or_url.url if hasattr(file_field_or_url, 'url') else str(file_field_or_url)
    if not url:
        return None

    if url.startswith('http://') or url.startswith('https://'):
        return url

    rel_path = url if url.startswith('/') else f'/{url}'

    configured_base = getattr(settings, 'MEDIA_BASE_URL', None) or os.getenv('MEDIA_BASE_URL', '').rstrip('/')
    if configured_base:
        return f"{configured_base}{rel_path}"

    if request is not None:
        try:
            return request.build_absolute_uri(rel_path)
        except Exception:
            pass

    return rel_path

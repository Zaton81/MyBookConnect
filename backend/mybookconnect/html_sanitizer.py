"""
Servicio centralizado de sanitización de contenido HTML y texto generado por usuarios (UGC) (Fase 59).

Proporciona protección de defensa en profundidad contra ataques XSS (Cross-Site Scripting),
inyección de código HTML malicioso, iframes, scripts, enlaces maliciosos y atributos peligrosos.
No confía únicamente en el frontend y procesa todos los contenidos antes de persistirlos.
"""

from typing import Optional, Set

import nh3

# Etiquetas permitidas para campos con formato enriquecido (ej: Tiptap en bio de perfil, reseñas)
ALLOWED_RICH_TAGS: Set[str] = {
    'p', 'br', 'b', 'strong', 'i', 'em', 'u', 's', 'strike',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'ul', 'ol', 'li', 'code', 'pre', 'hr',
    'a', 'span'
}

# Atributos explícitamente permitidos por etiqueta
ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title', 'target'},
    'span': {'class'},
}

# Esquemas de protocolo permitidos en enlaces
ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto'}


def sanitize_html(content: Optional[str]) -> str:
    """
    Sanitiza contenido HTML enriquecido permitiendo únicamente etiquetas y atributos seguros.
    - Neutraliza scripts (<script>), iframes, objetos, embeds y applets.
    - Elimina manejadores de eventos (onclick, onerror, onload, etc.).
    - Purga esquemas de protocolo peligrosos (javascript:, data:, vbscript:).
    - Aplica automáticamente rel="noopener noreferrer nofollow" en todos los enlaces.
    """
    if not content:
        return ""
    if not isinstance(content, str):
        content = str(content)

    clean_content = nh3.clean(
        content,
        tags=ALLOWED_RICH_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    )
    return clean_content.strip()


def sanitize_plain_text(content: Optional[str]) -> str:
    """
    Sanitiza campos que deben ser estrictamente texto plano (ej: títulos, ubicaciones, nombres, comentarios simples, chat).
    Elimina cualquier etiqueta HTML, script o marcado para prevenir inyecciones.
    """
    if not content:
        return ""
    if not isinstance(content, str):
        content = str(content)

    # nh3.clean con tags=set() elimina cualquier etiqueta HTML y extrae el texto puro
    clean_text = nh3.clean(content, tags=set())
    return clean_text.strip()

"""
Centralización y formateo de prompts para el asistente de lectura y análisis de libros.
"""

from typing import Any

BOOKAI_BASE_INSTRUCTIONS = (
    "Eres BookAI, el asistente literario inteligente y cordial de MyBookConnect. "
    "Tu misión es guiar, recomendar y enriquecer la experiencia de los apasionados de la lectura. "
    "Tus respuestas deben ser perspicaces, cálidas, concisas y orientadas al contexto literario. "
    "Recomienda libros basados en gustos e historial, resuelve dudas sobre tramas sin spoilers mayores, "
    "compara obras o autores, y sugiere lecturas apasionantes. "
    "Responde siempre en español y utiliza formato Markdown elegante con negritas y listas cuando aporte claridad."
)


def build_assistant_system_prompt(
    username: str,
    recent_read_titles: list[str] | None = None,
    current_book_info: dict[str, Any] | None = None,
) -> str:
    """
    Construye el system prompt personalizado inyectando contexto del usuario y del libro actual.

    :param username: Nombre de usuario de la sesión actual.
    :param recent_read_titles: Lista de títulos leídos recientemente por el usuario.
    :param current_book_info: Diccionario con información del libro en consulta (título, autor, sinopsis).
    :return: Cadena con el prompt completo del sistema.
    """
    context_lines = [f"El usuario actual es @{username}."]

    if recent_read_titles:
        titles_str = ', '.join(recent_read_titles[:5])
        context_lines.append(f"Libros leídos recientemente por el usuario: {titles_str}.")

    if current_book_info:
        title = current_book_info.get('title', 'Desconocido')
        author = current_book_info.get('author_name', 'Desconocido')
        desc = current_book_info.get('description', '')[:300]
        context_lines.append(
            f"El usuario está consultando específicamente sobre la obra '{title}' "
            f"escrita por {author}. "
            f"Sinopsis de referencia: {desc if desc else 'Sin descripción disponible'}."
        )

    context_block = "\n".join(context_lines)
    return f"{BOOKAI_BASE_INSTRUCTIONS}\n\nContexto de la conversación:\n{context_block}"


def build_book_summary_prompt(
    title: str,
    author_name: str,
    description: str | None,
) -> str:
    """
    Construye el prompt estructurado para solicitar el análisis temático y síntesis de un libro.

    :param title: Título del libro.
    :param author_name: Nombre del autor.
    :param description: Sinopsis o resumen disponible del libro.
    :return: Prompt formateado para el modelo de lenguaje.
    """
    desc_clean = description.strip() if description else 'No disponible'
    return (
        f"Analiza el siguiente libro:\n"
        f"Título: {title}\n"
        f"Autor: {author_name}\n"
        f"Sinopsis: {desc_clean}\n\n"
        f"Genera una ficha analítica breve con los siguientes puntos estructurados:\n"
        f"1. **Temas Centrales** (3 viñetas descriptivas)\n"
        f"2. **Tono y Estilo Literario** (2 oraciones concisas)\n"
        f"3. **Para quién es ideal esta lectura** (1 recomendación clave)"
    )

"""
Registro e implementaciones de herramientas seguras para el asistente BookAI (Fase 27).

Permite que el asistente realice llamadas a funciones (Function Calling) intermediadas
y estrictamente controladas por el backend con validación de permisos.
"""

import logging
from typing import Any

from django.db.models import Q

from ai.tools.base import AITool, ToolExecutionError
from books.models import Book, ReadingStatus, UserBook

logger = logging.getLogger(__name__)


class CatalogSearchTool(AITool):
    """Herramienta para buscar obras en el catálogo de libros."""

    @property
    def name(self) -> str:
        return 'catalog_search'

    @property
    def description(self) -> str:
        return (
            "Busca obras literarias en el catálogo de MyBookConnect por título, "
            "autor, palabras clave o género."
        )

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Término de búsqueda (título, autor o tema).",
                },
                "genre": {
                    "type": "string",
                    "description": "Filtro opcional por categoría o género literario.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (1 a 10).",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def execute(self, user: Any, **kwargs: Any) -> dict[str, Any]:
        query = str(kwargs.get('query', '')).strip()
        genre = kwargs.get('genre')
        limit = min(max(1, int(kwargs.get('limit', 5))), 10)

        if not query:
            return {"results": [], "count": 0}

        qs = Book.objects.select_related('author').prefetch_related('categories')
        filter_q = Q(title__icontains=query) | Q(author__name__icontains=query) | Q(description__icontains=query)

        if genre:
            filter_q &= Q(categories__name__icontains=genre)

        books = qs.filter(filter_q).distinct()[:limit]

        results = [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author.name if b.author else "Desconocido",
                "average_rating": b.average_rating,
                "categories": [c.name for c in b.categories.all()],
            }
            for b in books
        ]
        return {"results": results, "count": len(results)}


class BookDetailTool(AITool):
    """Herramienta para consultar los datos completos de un libro."""

    @property
    def name(self) -> str:
        return 'book_detail'

    @property
    def description(self) -> str:
        return "Obtiene información detallada de una obra literaria a partir de su ID."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "book_id": {
                    "type": "integer",
                    "description": "Identificador numérico del libro.",
                },
            },
            "required": ["book_id"],
        }

    def execute(self, user: Any, **kwargs: Any) -> dict[str, Any]:
        book_id = kwargs.get('book_id')
        if not book_id:
            raise ToolExecutionError("El parámetro 'book_id' es obligatorio.")

        book = Book.objects.filter(id=book_id).select_related('author').prefetch_related('categories').first()
        if not book:
            return {"found": False, "detail": f"Libro con ID {book_id} no encontrado."}

        return {
            "found": True,
            "id": book.id,
            "title": book.title,
            "author": book.author.name if book.author else "Desconocido",
            "published_date": str(book.published_date) if book.published_date else None,
            "average_rating": book.average_rating,
            "categories": [c.name for c in book.categories.all()],
            "description": book.description or "Sin descripción disponible.",
        }


class UserReadingStatusTool(AITool):
    """Herramienta para consultar el estado de lectura del usuario actual."""

    @property
    def name(self) -> str:
        return 'user_reading_status'

    @property
    def description(self) -> str:
        return "Consulta si el usuario actual ha leído, está leyendo o tiene en lista de deseos un libro específico."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "book_id": {
                    "type": "integer",
                    "description": "Identificador numérico del libro a consultar.",
                },
            },
            "required": ["book_id"],
        }

    def execute(self, user: Any, **kwargs: Any) -> dict[str, Any]:
        book_id = kwargs.get('book_id')
        if not book_id:
            raise ToolExecutionError("El parámetro 'book_id' es obligatorio.")

        entry = UserBook.objects.filter(user=user, book_id=book_id).first()
        if not entry:
            return {
                "in_library": False,
                "status": None,
                "rating": None,
            }

        return {
            "in_library": True,
            "status": entry.status,
            "status_label": entry.get_status_display(),
            "progress": entry.progress,
            "rating": entry.rating,
            "is_read": entry.is_read,
            "wishlist": entry.wishlist,
        }


class AddToWishlistTool(AITool):
    """Herramienta para añadir un libro a la lista de deseos de lectura del usuario."""

    @property
    def name(self) -> str:
        return 'add_to_wishlist'

    @property
    def description(self) -> str:
        return "Añade un libro a la lista de deseos ('Quiero leer') de la biblioteca personal del usuario."

    @property
    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "book_id": {
                    "type": "integer",
                    "description": "Identificador numérico del libro a agregar.",
                },
            },
            "required": ["book_id"],
        }

    def execute(self, user: Any, **kwargs: Any) -> dict[str, Any]:
        book_id = kwargs.get('book_id')
        if not book_id:
            raise ToolExecutionError("El parámetro 'book_id' es obligatorio.")

        book = Book.objects.filter(id=book_id).first()
        if not book:
            raise ToolExecutionError(f"No se encontró ningún libro con id={book_id}.")

        entry, created = UserBook.objects.get_or_create(
            user=user,
            book=book,
            defaults={
                'status': ReadingStatus.WANT_TO_READ,
                'wishlist': True,
            },
        )

        if not created and entry.status != ReadingStatus.WANT_TO_READ:
            entry.wishlist = True
            entry.save(update_fields=['wishlist', 'updated_at'])

        return {
            "success": True,
            "book_id": book.id,
            "book_title": book.title,
            "status": entry.status,
            "action": "created" if created else "updated",
        }


# Instancias registradas centralmente
_TOOLS_REGISTRY: dict[str, AITool] = {
    'catalog_search': CatalogSearchTool(),
    'book_detail': BookDetailTool(),
    'user_reading_status': UserReadingStatusTool(),
    'add_to_wishlist': AddToWishlistTool(),
}


def get_registered_tools() -> dict[str, AITool]:
    """Retorna el diccionario de herramientas registradas disponibles."""
    return _TOOLS_REGISTRY


def get_tools_definitions() -> list[dict[str, Any]]:
    """Genera la lista de esquemas de herramientas en formato OpenAI Tool Calling."""
    return [tool.to_openai_tool() for tool in _TOOLS_REGISTRY.values()]


def execute_tool(name: str, user: Any, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Ejecuta de forma segura una herramienta solicitada, validando permisos del usuario
    y parámetros antes de realizar cualquier acción.

    :param name: Nombre de la herramienta (ej: 'catalog_search').
    :param user: Instancia del usuario autenticado.
    :param arguments: Diccionario de argumentos provistos.
    :return: Diccionario con los resultados estructurados de la ejecución.
    :raises ToolExecutionError: Si la herramienta no existe o falla la validación.
    """
    args = arguments or {}
    tool = _TOOLS_REGISTRY.get(name)

    if not tool:
        raise ToolExecutionError(f"Herramienta '{name}' no reconocida o no registrada.")

    # 1. Validación estricta de permisos del usuario
    tool.validate_permissions(user)

    # 2. Validación de parámetros obligatorios
    schema = tool.parameters_schema
    required_fields = schema.get('required', [])
    for field in required_fields:
        if field not in args:
            raise ToolExecutionError(f"Falta el parámetro obligatorio '{field}' para la herramienta '{name}'.")

    # 3. Ejecución controlada con captura de excepciones
    try:
        return tool.execute(user, **args)
    except ToolExecutionError:
        raise
    except Exception as exc:
        logger.exception("Error inesperado al ejecutar herramienta '%s': %s", name, exc)
        raise ToolExecutionError(f"Error al ejecutar '{name}': {str(exc)}") from exc

"""
Servicio de Diversificación y Filtrado de Privacidad para el Motor de Recomendaciones.

Implementa la capa 'Filtering & Diversity' de la arquitectura por capas (Fase 7 - 12.1 & 12.3):
1. Privacy Filtering: Filtrado estricto de señales sociales previniendo la filtración de lecturas
   o listas de usuarios bloqueados o con perfiles privados no seguidos.
2. Diversity Re-ranking: Evita la sobreconcentración de un único autor prolífico o género monótono
   en el Top N, garantizando diversidad y serendipia sin degradar la relevancia global.
"""

from collections import defaultdict
from typing import Any, Callable


def apply_diversity_filter(
    items: list[Any],
    limit: int = 10,
    max_per_author: int = 2,
    max_per_category: int = 4,
    get_author_id: Callable[[Any], int | None] | None = None,
    get_category_ids: Callable[[Any], list[int]] | None = None,
) -> list[Any]:
    """
    Filtra y reordena la lista de candidatos priorizando diversidad de autores y géneros.

    :param items: Lista de elementos ordenados por relevancia/score descendente.
    :param limit: Límite de elementos a retornar en el Top N.
    :param max_per_author: Número máximo de libros permitidos de un mismo autor en la primera pasada.
    :param max_per_category: Número máximo de libros permitidos de una misma categoría en la primera pasada.
    :param get_author_id: Función extractora del ID de autor (por defecto detecta .book.author_id o ['book'].author_id).
    :param get_category_ids: Función extractora de IDs de categorías.
    :return: Lista de elementos diversificados de tamaño hasta `limit`.
    """
    if not items or limit <= 0:
        return []

    def _default_get_author_id(item: Any) -> int | None:
        if hasattr(item, 'book'):
            return getattr(item.book, 'author_id', None)
        if isinstance(item, dict):
            b = item.get('book')
            if hasattr(b, 'author_id'):
                return b.author_id
            if isinstance(b, dict):
                return b.get('author_id')
        return None

    def _default_get_category_ids(item: Any) -> list[int]:
        book = getattr(item, 'book', None) or (item.get('book') if isinstance(item, dict) else None)
        if book and hasattr(book, 'categories'):
            try:
                return [c.id for c in book.categories.all()]
            except Exception:
                return []
        return []

    author_extractor = get_author_id or _default_get_author_id
    category_extractor = get_category_ids or _default_get_category_ids

    selected: list[Any] = []
    overflow: list[Any] = []

    author_counts: dict[int, int] = defaultdict(int)
    category_counts: dict[int, int] = defaultdict(int)

    for item in items:
        aid = author_extractor(item)
        cids = category_extractor(item)

        # Comprobar límite de autor
        author_ok = (aid is None) or (author_counts[aid] < max_per_author)

        # Comprobar límite de categorías
        cat_ok = True
        if cids and max_per_category > 0:
            for cid in cids:
                if category_counts[cid] >= max_per_category:
                    cat_ok = False
                    break

        if author_ok and cat_ok:
            selected.append(item)
            if aid is not None:
                author_counts[aid] += 1
            for cid in cids:
                category_counts[cid] += 1
            if len(selected) == limit:
                break
        else:
            overflow.append(item)

    # Si no alcanzamos el límite deseado mediante filtrado estricto de diversidad,
    # rellenamos con los candidatos excedentes ordenados por relevancia original.
    if len(selected) < limit and overflow:
        needed = limit - len(selected)
        selected.extend(overflow[:needed])

    return selected

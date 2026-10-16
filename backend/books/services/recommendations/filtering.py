"""
Etapa 2 del Pipeline de Recomendaciones: Filtrado y Exclusiones Estrictas.

Excluye libros ya leídos o en curso, libros descartados por el usuario
y aplica restricciones de facetas (categoría, longitud de páginas).
"""

from typing import Any

from books.models import ReadingStatus, RecommendationFeedback, UserBook


class RecommendationFilter:
    """Filtro de higiene y restricciones para candidatos a recomendación."""

    @staticmethod
    def get_excluded_book_ids(user: Any, exclude_dismissed: bool = True) -> set[int]:
        """
        Retorna el conjunto de IDs de libros que NO deben recomendarse al usuario.
        """
        if not user or not user.is_authenticated:
            return set()

        # 1. Libros ya leídos, en lectura o abandonados por el usuario
        consumed_ids = set(
            UserBook.objects.filter(
                user=user,
                status__in=[ReadingStatus.READ, ReadingStatus.READING, ReadingStatus.ABANDONED],
            ).values_list('book_id', flat=True)
        )

        # 2. Libros descartados explícitamente ("no me interesa")
        dismissed_ids = set()
        if exclude_dismissed:
            from books.models import RecommendationFeedbackAction

            dismissed_ids = set(
                RecommendationFeedback.objects.filter(
                    user=user,
                    action=RecommendationFeedbackAction.DISMISSED,
                ).values_list('book_id', flat=True)
            )

        return consumed_ids | dismissed_ids

    @staticmethod
    def filter_by_criteria(
        candidates: list[dict[str, Any]],
        excluded_ids: set[int],
        category_id: int | str | None = None,
        length_tier: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Filtra la lista de candidatos eliminando IDs excluidos y aplicando filtros opcionales.
        """
        filtered: list[dict[str, Any]] = []

        cat_id_int = int(category_id) if category_id and str(category_id).isdigit() else None
        tier = (length_tier or '').lower().strip()

        for cand in candidates:
            book = cand.get('book')
            if not book:
                continue

            book_id = getattr(book, 'id', None) or (book.get('id') if isinstance(book, dict) else None)
            if not book_id or book_id in excluded_ids:
                continue

            # Filtro por categoría
            if cat_id_int is not None:
                if hasattr(book, 'categories'):
                    cand_cats = {c.id for c in book.categories.all()}
                elif isinstance(book, dict):
                    cand_cats = {c['id'] if isinstance(c, dict) else c for c in book.get('categories', [])}
                else:
                    cand_cats = set()

                if cat_id_int not in cand_cats:
                    continue

            # Filtro por longitud de páginas
            if tier:
                page_count = getattr(book, 'page_count', None) or (book.get('page_count') if isinstance(book, dict) else None)
                if page_count:
                    if tier == 'short' and page_count > 200:
                        continue
                    elif tier == 'medium' and not (200 <= page_count <= 450):
                        continue
                    elif tier == 'long' and not (450 < page_count <= 800):
                        continue
                    elif tier == 'epic' and page_count <= 800:
                        continue

            filtered.append(cand)

        return filtered

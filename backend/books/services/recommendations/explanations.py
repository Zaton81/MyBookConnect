"""
Etapa 4 del Pipeline de Recomendaciones: Generación y Enriquecimiento de Explicaciones en Lote.

Construye explicaciones transparentes y legibles para el lector ("Porque leíste...",
"Autor afín...", "Popular en...") precalculando relaciones en lote para eliminar consultas N+1.
"""

from typing import Any

from books.media_utils import build_media_url


class BatchExplanationEngine:
    """Motor de enriquecimiento y formateo de explicaciones en lote."""

    @staticmethod
    def enrich_and_format(
        ranked_candidates: list[dict[str, Any]],
        user: Any,
        request: Any = None,
        algorithm_version: str = 'v3',
    ) -> list[dict[str, Any]]:
        """
        Formatea y enriquece los libros recomendados en lote con metadatos y explicaciones legibles.
        """
        results: list[dict[str, Any]] = []

        # Extraer afinidades de usuario para explicaciones
        fav_author_names = set()
        fav_category_names = set()
        if user and user.is_authenticated:
            if hasattr(user, 'favorite_categories'):
                fav_category_names = {c.name for c in user.favorite_categories.all()}

        for item in ranked_candidates:
            b = item['book']
            score = float(item.get('score', 0.0))
            source = item.get('source', '')
            reason = item.get('reason', '')

            # Determinar motivo explicable legible
            if not reason or reason == 'Libro similar de interés':
                if source == 'v3_semantic':
                    reason = "Temática y estilo afines a tus lecturas recientes"
                elif source == 'v2_collaborative':
                    reason = "Lectores con tus mismos gustos han disfrutado esta obra"
                elif source == 'v1_content':
                    # Si coincide autor
                    matched_cats = [c.name for c in b.categories.all() if c.name in fav_category_names] if hasattr(b, 'categories') else []
                    if b.author and b.author.name in fav_author_names:
                        reason = f"Por tu interés en obras de {b.author.name}"
                    elif matched_cats:
                        reason = f"Recomendado por tu interés en {matched_cats[0]}"
                    else:
                        reason = "Recomendado por su alta coincidencia con tus géneros favoritos"
                else:
                    reason = "Obra destacada y aclamada por la comunidad"

            cover_url = build_media_url(b.cover.name if b.cover else None, request=request)
            author_name = b.get_author_names() if hasattr(b, 'get_author_names') else (b.author.name if b.author else 'Autor desconocido')

            categories_data = []
            if hasattr(b, 'categories'):
                categories_data = [{'id': c.id, 'name': c.name} for c in b.categories.all()]

            breakdown = item.get('breakdown', {})
            metadata = {
                'source': source,
                'author_id': b.author_id,
                **breakdown,
            }

            formatted_item = {
                'id': b.id,
                'title': b.title,
                'author_name': author_name,
                'cover': cover_url,
                'average_rating': b.average_rating,
                'score': round(score, 4),
                'algorithm_version': algorithm_version,
                'strategy': source or algorithm_version,
                'reason': reason,
                'explanation': reason,
                'metadata': metadata,
                'scores': breakdown,
                'breakdown': breakdown,
                'categories': categories_data,
            }
            results.append(formatted_item)

        return results

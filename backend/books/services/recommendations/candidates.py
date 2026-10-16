"""
Etapa 1 del Pipeline de Recomendaciones: Generación Rápida de Candidatos (K = 200).

Combina múltiples estrategias de recuperación:
- Similitud semántica vectorial (v3) mediante UserPreferenceEmbedding y BookEmbedding.
- Filtrado colaborativo e historial social de co-lecturas (v2).
- Afinidad temática de autores y categorías (v1).
- Estrategia de arranque en frío (Cold-Start) basada en valoración media y popularidad.
"""

import logging
from typing import Any

from books.models import Book
from books.services.recommendation_v1_service import RecommendationEngineV1
from books.services.recommendation_v2_service import RecommendationEngineV2
from books.services.recommendation_v3_service import RecommendationEngineV3, _get_vector_from_book

logger = logging.getLogger(__name__)


class CandidateGenerator:
    """Generador multicanal de candidatos a recomendación."""

    def __init__(self):
        self.engine_v1 = RecommendationEngineV1()
        self.engine_v2 = RecommendationEngineV2()
        self.engine_v3 = RecommendationEngineV3()

    def generate_candidates(
        self,
        user: Any,
        k: int = 200,
        strategy: str = 'hybrid',
    ) -> list[dict[str, Any]]:
        """
        Recupera hasta K candidatos combinando las fuentes según la estrategia seleccionada.
        """
        candidates_by_id: dict[int, dict[str, Any]] = {}

        def _register_items(items: list[Any], source_label: str):
            for item in items:
                if isinstance(item, dict):
                    b_id = item.get('id')
                    if not b_id:
                        continue
                    b = Book.objects.filter(id=b_id).select_related('author').prefetch_related('categories', 'authors').first()
                    if not b:
                        continue
                    score = float(item.get('score', 0.0))
                    reason = str(item.get('reason', ''))
                    breakdown = item.get('breakdown') or item.get('scores') or {}
                else:
                    b = getattr(item, 'book', None)
                    if not b:
                        continue
                    score = float(getattr(item, 'score', 0.0))
                    reason = str(getattr(item, 'reason', ''))
                    breakdown = item.breakdown.to_dict() if hasattr(item, 'breakdown') and hasattr(item.breakdown, 'to_dict') else {}

                if b.id not in candidates_by_id:
                    candidates_by_id[b.id] = {
                        'book': b,
                        'score': score,
                        'vector': _get_vector_from_book(b),
                        'source': source_label,
                        'breakdown': breakdown,
                        'reason': reason,
                    }
                else:
                    candidates_by_id[b.id]['score'] = max(candidates_by_id[b.id]['score'], score)

        # 1. Recuperar candidatos semánticos v3 si el usuario está autenticado
        if strategy in ('v3', 'hybrid', 'semantic', 'semantic_v3', 'vector', 'hybrid_v3') and user and user.is_authenticated:
            try:
                v3_results = self.engine_v3.recommend(user=user, limit=min(k, 100))
                _register_items(v3_results, 'v3_semantic')
            except Exception as exc:
                logger.warning("Fallo al generar candidatos semánticos v3: %s", exc)

        # 2. Recuperar candidatos colaborativos v2
        if strategy in ('v2', 'hybrid', 'collaborative', 'collab', 'social') and user and user.is_authenticated:
            try:
                v2_results = self.engine_v2.recommend(user=user, limit=min(k, 100))
                _register_items(v2_results, 'v2_collaborative')
            except Exception as exc:
                logger.warning("Fallo al generar candidatos colaborativos v2: %s", exc)

        # 3. Recuperar candidatos canónicos v1 (heurísticas de género, autor)
        if strategy in ('v1', 'hybrid', 'canonical_v1', 'rules', 'serendipity', 'discovery') or not candidates_by_id:
            try:
                v1_results = self.engine_v1.recommend(user=user, limit=min(k, 100))
                _register_items(v1_results, 'v1_content')
            except Exception as exc:
                logger.warning("Fallo al generar candidatos canónicos v1: %s", exc)

        # 4. Fallback de arranque en frío (Cold-Start) si faltan candidatos
        if len(candidates_by_id) < 20:
            cold_qs = (
                Book.objects.filter(average_rating__gte=3.5)
                .select_related('author')
                .prefetch_related('categories', 'authors')
                .order_by('-average_rating', '-created_at')[:k]
            )
            for b in cold_qs:
                if b.id not in candidates_by_id:
                    score = (b.average_rating or 3.5) / 5.0
                    candidates_by_id[b.id] = {
                        'book': b,
                        'score': score,
                        'vector': _get_vector_from_book(b),
                        'source': 'cold_start',
                        'breakdown': {'cold_start_score': score},
                        'reason': 'Aclamado por la comunidad de lectores',
                    }

        candidates = list(candidates_by_id.values())
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates[:k]

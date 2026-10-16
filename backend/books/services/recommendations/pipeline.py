"""
Orquestador del Pipeline de Recomendaciones en 4 Etapas:
1. Candidates (Generación rápida K=200)
2. Filtering (Exclusiones estrictas y facetas)
3. Reranking (Diversidad y Maximal Marginal Relevance MMR)
4. Explanations (Enriquecimiento explicable en lote)
"""

import logging
from typing import Any

from django.core.cache import cache

from books.cache_utils import TTL_RECOMMENDATIONS, user_recommendations_key

from .candidates import CandidateGenerator
from .explanations import BatchExplanationEngine
from .filtering import RecommendationFilter
from .reranking import MMRReranker

logger = logging.getLogger(__name__)


class RecommendationPipeline:
    """Pipeline integral de recomendación de libros."""

    def __init__(self):
        self.candidate_generator = CandidateGenerator()
        self.filter = RecommendationFilter()
        self.reranker = MMRReranker()
        self.explanation_engine = BatchExplanationEngine()

    def run(
        self,
        user: Any,
        limit: int = 10,
        strategy: str = 'hybrid',
        category_id: int | str | None = None,
        length_tier: str | None = None,
        exclude_dismissed: bool = True,
        lambda_param: float = 0.7,
        request: Any = None,
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Ejecuta las 4 etapas del pipeline de recomendaciones.
        """
        cache_key = None
        if use_cache and user and user.is_authenticated:
            cat_suffix = f"_c{category_id}" if category_id else ""
            tier_suffix = f"_t{length_tier}" if length_tier else ""
            cache_key = f"{user_recommendations_key(user.id)}_{strategy}_{limit}{cat_suffix}{tier_suffix}"
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        # 1. Candidatos
        raw_candidates = self.candidate_generator.generate_candidates(
            user=user,
            k=200,
            strategy=strategy,
        )

        # 2. Filtrado
        excluded_ids = self.filter.get_excluded_book_ids(user, exclude_dismissed=exclude_dismissed)
        filtered_candidates = self.filter.filter_by_criteria(
            candidates=raw_candidates,
            excluded_ids=excluded_ids,
            category_id=category_id,
            length_tier=length_tier,
        )

        # 3. Reranking por MMR y diversidad
        reranked_candidates = self.reranker.rerank_mmr(
            candidates=filtered_candidates,
            limit=limit,
            lambda_param=lambda_param,
        )

        # 4. Explicaciones y formateo
        algo_version = 'v3' if strategy in ('v3', 'semantic_v3', 'vector', 'hybrid_v3') else ('v2' if strategy in ('v2', 'collab') else 'v1')
        final_results = self.explanation_engine.enrich_and_format(
            ranked_candidates=reranked_candidates,
            user=user,
            request=request,
            algorithm_version=algo_version,
        )

        if cache_key and final_results:
            cache.set(cache_key, final_results, timeout=TTL_RECOMMENDATIONS)

        return final_results

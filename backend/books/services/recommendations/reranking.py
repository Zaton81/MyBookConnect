"""
Etapa 3 del Pipeline de Recomendaciones: Re-ranking y Diversificación (MMR).

Aplica la fórmula de Maximal Marginal Relevance (MMR) para balancear
relevancia individual y novedad frente a los libros ya seleccionados,
evitando la sobreconcentración de un mismo autor o género.
"""

from typing import Any

from ai.embeddings import cosine_similarity
from books.services.recommendation_diversity_service import apply_diversity_filter


class MMRReranker:
    """Reordenador por diversidad y relevancia marginal máxima."""

    @staticmethod
    def calculate_pairwise_similarity(vec_a: list[float] | None, vec_b: list[float] | None) -> float:
        """Calcula similitud coseno entre dos vectores de libros."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        return max(0.0, float(cosine_similarity(vec_a, vec_b)))

    @classmethod
    def rerank_mmr(
        cls,
        candidates: list[dict[str, Any]],
        limit: int = 10,
        lambda_param: float = 0.7,
        max_per_author: int = 2,
        max_per_category: int = 4,
    ) -> list[dict[str, Any]]:
        """
        Aplica Maximal Marginal Relevance (MMR) sobre el conjunto de candidatos.

        :param candidates: Lista de diccionarios con 'book', 'score' y 'vector'.
        :param limit: Cantidad final de recomendaciones a retornar.
        :param lambda_param: Factor de balance entre relevancia (lambda) y diversidad (1 - lambda).
        :param max_per_author: Restricción dura de diversidad por autor.
        :param max_per_category: Restricción dura de diversidad por categoría.
        :return: Lista reordenada de candidatos seleccionados.
        """
        if not candidates or limit <= 0:
            return []

        # Paso 1: Filtrado de diversidad estructural (autor / categoría)
        pre_filtered = apply_diversity_filter(
            items=candidates,
            limit=min(len(candidates), limit * 3),
            max_per_author=max_per_author,
            max_per_category=max_per_category,
        )
        if not pre_filtered:
            pre_filtered = candidates

        # Si no hay vectores disponibles, ordenar por score directamente
        has_vectors = any(c.get('vector') for c in pre_filtered)
        if not has_vectors or len(pre_filtered) <= 1:
            pre_filtered.sort(key=lambda x: x.get('score', 0.0), reverse=True)
            return pre_filtered[:limit]

        # Paso 2: Selección greedy por MMR
        selected: list[dict[str, Any]] = []
        remaining = list(pre_filtered)

        # Seleccionar el primer elemento con mayor score de relevancia
        first = max(remaining, key=lambda x: x.get('score', 0.0))
        selected.append(first)
        remaining.remove(first)

        while len(selected) < limit and remaining:
            best_mmr = -float('inf')
            best_cand = None

            for cand in remaining:
                relevance = cand.get('score', 0.0)
                cand_vec = cand.get('vector')

                # Máxima similitud con cualquiera de los ya seleccionados
                max_sim_to_selected = 0.0
                if cand_vec:
                    for s in selected:
                        s_vec = s.get('vector')
                        if s_vec:
                            sim = cls.calculate_pairwise_similarity(cand_vec, s_vec)
                            if sim > max_sim_to_selected:
                                max_sim_to_selected = sim

                mmr_score = (lambda_param * relevance) - ((1.0 - lambda_param) * max_sim_to_selected)
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_cand = cand

            if best_cand is not None:
                selected.append(best_cand)
                remaining.remove(best_cand)
            else:
                break

        return selected

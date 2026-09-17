"""
Motor de Recomendaciones v3 para MyBookConnect.

Fase 51 del Roadmap: Embeddings Semánticos y Vector de Preferencias de Usuario
(User Preference Embedding & Semantic Vector Matching):
    Libros Consumidos -> Promedio Ponderado -> User Preference Embedding U -> Similitud Coseno -> Candidatos -> Fusión Tri-Híbrida v3

Fórmula del vector de preferencias de usuario:
    U = sum(w_i * E(B_i)) / sum(w_i)
    donde w_i prioriza:
    - Libros con rating 5 estrellas: 1.50
    - Libros con rating 4 estrellas: 1.20
    - Libros terminados (READ): 1.00
    - Libros en curso (READING): 0.70
    - Libros en lista de deseos (WANT_TO_READ): 0.50

Similitud semántica con candidatos:
    S_semantic(B) = max(0.0, cosine_similarity(U_hat, E(B)))

Fusión Tri-Híbrida v3:
    S_v3 = 0.45 * S_semantic + 0.30 * S_collab + 0.25 * S_content_v1

Versión del algoritmo: 'v3'
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.db.models import Count

from ai.embeddings import cosine_similarity
from books.cache_utils import TTL_RECOMMENDATIONS, user_recommendations_key
from books.media_utils import build_media_url
from books.models import Book, ReadingStatus, UserBook
from books.services.recommendation_v1_service import (
    RecommendationEngineV1,
)
from books.services.recommendation_v2_service import (
    RecommendationEngineV2,
    ScoreBreakdownV2,
)

logger = logging.getLogger(__name__)

ALGORITHM_VERSION_V3 = "v3"


@dataclass
class UserPreferenceVector:
    """Representa el vector de embedding condensado de preferencias de un usuario."""
    vector: list[float] | None = None
    dimension: int = 0
    books_count: int = 0
    weights_sum: float = 0.0

    @property
    def has_vector(self) -> bool:
        return bool(self.vector and len(self.vector) > 0)

    @property
    def has_embedding(self) -> bool:
        return self.has_vector

    @property
    def books_analyzed(self) -> int:
        return self.books_count

    @property
    def books_used(self) -> int:
        return self.books_count

    @property
    def dimensions(self) -> int:
        return self.dimension

    def to_dict(self) -> dict[str, Any]:
        return {
            'has_embedding': self.has_embedding,
            'has_vector': self.has_vector,
            'dimension': self.dimension,
            'dimensions': self.dimensions,
            'books_count': self.books_count,
            'books_used': self.books_used,
            'books_analyzed': self.books_analyzed,
            'weights_sum': round(self.weights_sum, 4),
            'sample_components': [round(x, 4) for x in self.vector[:5]] if self.vector else [],
            'vector': self.vector if self.has_vector else None,
            'algorithm_version': ALGORITHM_VERSION_V3,
        }

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)


@dataclass
class ScoreBreakdownV3:
    semantic_score: float = 0.0
    collaborative_score: float = 0.0
    content_v1_score: float = 0.0
    has_user_embedding: bool = False
    v2_breakdown: ScoreBreakdownV2 = field(default_factory=ScoreBreakdownV2)

    def to_dict(self) -> dict[str, Any]:
        res = {
            'semantic': round(self.semantic_score, 4),
            'collaborative': round(self.collaborative_score, 4),
            'content_v1': round(self.content_v1_score, 4),
            'has_user_embedding': self.has_user_embedding,
        }
        res.update(self.v2_breakdown.to_dict())
        return res


@dataclass
class RecommendationV3Item:
    book: Book
    score: float
    reason: str
    algorithm_version: str = ALGORITHM_VERSION_V3
    breakdown: ScoreBreakdownV3 = field(default_factory=ScoreBreakdownV3)

    def to_dict(self, request=None) -> dict[str, Any]:
        b = self.book
        cover_url = build_media_url(b.cover.name if b.cover else None, request=request)
        return {
            'id': b.id,
            'title': b.title,
            'author_name': b.author.name if b.author else 'Autor desconocido',
            'cover': cover_url,
            'average_rating': b.average_rating,
            'score': round(self.score, 4),
            'algorithm_version': self.algorithm_version,
            'breakdown': self.breakdown.to_dict(),
            'scores': self.breakdown.to_dict(),
            'reason': self.reason,
        }


class RecommendationEngineV3:
    """
    Motor de Recomendaciones v3: Embeddings semánticos, vector sintético de preferencias
    de usuario y fusión tri-híbrida con señales colaborativas v2 y canónicas v1.
    """

    def __init__(
        self,
        user=None,
        weight_semantic: float = 0.45,
        weight_collab: float = 0.30,
        weight_content: float = 0.25,
    ):
        self.user = user
        total = weight_semantic + weight_collab + weight_content
        if total > 0:
            self.w_semantic = weight_semantic / total
            self.w_collab = weight_collab / total
            self.w_content = weight_content / total
        else:
            self.w_semantic, self.w_collab, self.w_content = 0.45, 0.30, 0.25

        self.engine_v1 = RecommendationEngineV1()
        self.engine_v2 = RecommendationEngineV2(collaborative_weight=0.50)

    def get_user_preference_vector(self, user=None) -> UserPreferenceVector:
        target = user or self.user
        res = self.compute_user_preference_embedding(target)
        if res is None:
            return UserPreferenceVector(vector=None, dimension=0, books_count=0, weights_sum=0.0)
        return res

    def calculate_semantic_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        return max(0.0, float(cosine_similarity(vec_a, vec_b)))

    def compute_user_preference_embedding(self, user) -> UserPreferenceVector | None:
        """
        Calcula el vector de preferencias del usuario como el promedio ponderado
        de los embeddings de los libros con los que ha interactuado:
        - Libros con rating 5: peso 1.50
        - Libros con rating 4: peso 1.20
        - Libros leídos (READ): peso 1.00
        - Libros en lectura (READING): peso 0.70
        - Libros en lista de deseos (WANT_TO_READ): peso 0.50
        """
        if not user or not user.is_authenticated:
            return None

        cache_key = f"user_pref_embedding_{user.id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        user_entries = (
            UserBook.objects.filter(user=user)
            .select_related('book')
            .exclude(book__embedding__isnull=True)
        )

        weighted_components: list[float] | None = None
        weights_sum = 0.0
        books_count = 0
        dimension = 0

        for entry in user_entries:
            emb = entry.book.embedding
            if not emb or not isinstance(emb, list) or len(emb) == 0:
                continue

            dim = len(emb)
            if dimension == 0:
                dimension = dim
                weighted_components = [0.0] * dimension
            elif dim != dimension:
                # Omitir vectores con discrepancia de dimensiones
                continue

            # Factor de ponderación
            if entry.rating:
                if entry.rating >= 5:
                    w = 1.50
                elif entry.rating >= 4:
                    w = 1.20
                elif entry.rating >= 3:
                    w = 0.90
                else:
                    w = 0.30
            elif entry.status == ReadingStatus.READ:
                w = 1.00
            elif entry.status == ReadingStatus.READING:
                w = 0.70
            elif entry.status == ReadingStatus.WANT_TO_READ:
                w = 0.50
            else:
                w = 0.20

            for i in range(dimension):
                weighted_components[i] += (emb[i] * w)

            weights_sum += w
            books_count += 1

        if not weighted_components or weights_sum == 0 or books_count == 0:
            return None

        # Promedio ponderado
        avg_vector = [val / weights_sum for val in weighted_components]

        # Normalización a norma euclídea unitaria
        norm = math.sqrt(sum(x * x for x in avg_vector))
        if norm > 0:
            unit_vector = [x / norm for x in avg_vector]
        else:
            unit_vector = avg_vector

        result = UserPreferenceVector(
            vector=unit_vector,
            dimension=dimension,
            books_count=books_count,
            weights_sum=weights_sum,
        )

        cache.set(cache_key, result, timeout=TTL_RECOMMENDATIONS)
        return result

    def score_candidate_semantic(self, book: Book, user_pref_vector: UserPreferenceVector | None) -> float:
        """
        Calcula la afinidad semántica vectorial entre el vector de preferencias
        del usuario y el vector del libro candidato.
        """
        if not user_pref_vector or not user_pref_vector.vector:
            return 0.0

        book_emb = book.embedding
        if not book_emb or not isinstance(book_emb, list) or len(book_emb) != user_pref_vector.dimension:
            return 0.0

        sim = cosine_similarity(user_pref_vector.vector, book_emb)
        return max(0.0, float(sim))

    def recommend(
        self,
        user,
        limit: int = 10,
        request=None,
    ) -> list[dict[str, Any]]:
        """
        Genera el listado ordenado de recomendaciones v3:
        Fusión tri-híbrida de similitud semántica (vectorial), colaborativa v2 y reglas canónicas v1.
        """
        if not user or not user.is_authenticated:
            return []

        cache_key = user_recommendations_key(user.id, strategy='v3')
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 1. Vector de preferencias semánticas del usuario
        user_pref = self.compute_user_preference_embedding(user)
        has_semantic = user_pref is not None and user_pref.books_count > 0

        # 2. Perfil de contenidos v1 y exclusión de biblioteca
        profile_v1 = self.engine_v1.compute_user_profile(user)

        # 3. Señales colaborativas v2
        similar_peers = self.engine_v2.find_similar_users(user=user, limit=20)
        collab_data_map = self.engine_v2.get_collaborative_candidate_scores(user=user, similar_peers=similar_peers)

        # 4. Universo de candidatos
        candidate_ids = set(collab_data_map.keys())
        if len(candidate_ids) < 60:
            extra_ids = (
                Book.objects.exclude(id__in=profile_v1.excluded_book_ids)
                .values_list('id', flat=True)[:150]
            )
            candidate_ids.update(extra_ids)

        candidate_books = (
            Book.objects.filter(id__in=candidate_ids)
            .exclude(id__in=profile_v1.excluded_book_ids)
            .select_related('author')
            .prefetch_related('categories')
        )

        # Pesos dinámicos adaptados según disponibilidad de embeddings y pares
        if has_semantic and similar_peers:
            w_sem, w_col, w_con = self.w_semantic, self.w_collab, self.w_content
        elif has_semantic and not similar_peers:
            w_sem, w_col, w_con = 0.65, 0.0, 0.35
        elif not has_semantic and similar_peers:
            w_sem, w_col, w_con = 0.0, 0.55, 0.45
        else:
            w_sem, w_col, w_con = 0.0, 0.0, 1.0

        v3_items: list[RecommendationV3Item] = []

        for book in candidate_books:
            # Puntuación semántica vectorial
            s_semantic = self.score_candidate_semantic(book, user_pref) if has_semantic else 0.0

            # Puntuación colaborativa
            collab_info = collab_data_map.get(book.id)
            s_collab = collab_info['score'] if collab_info else 0.0
            peers_list = collab_info['peers'] if collab_info else []
            peers_count = collab_info['peers_count'] if collab_info else 0

            # Puntuación de contenidos v1
            v1_item = self.engine_v1.score_candidate(book, profile_v1)
            s_content = v1_item.score

            # Suma tri-híbrida ponderada
            final_score = (w_sem * s_semantic) + (w_col * s_collab) + (w_con * s_content)

            # Explicabilidad inteligente orientada al factor dominante
            if has_semantic and s_semantic >= 0.70 and (w_sem * s_semantic) >= (w_col * s_collab):
                reason = "Afinidad semántica profunda con los temas y estilo de tus libros favoritos"
            elif s_collab > 0.4 and peers_list:
                top_peer = peers_list[0]
                reason = f"Recomendado por lectores con afinidad demostrada a tus gustos (@{top_peer})"
            else:
                reason = v1_item.reason

            breakdown_v2 = ScoreBreakdownV2(
                collaborative_score=s_collab,
                content_v1_score=s_content,
                shared_peer_count=peers_count,
                top_peer_username=peers_list[0] if peers_list else None,
                v1_breakdown=v1_item.breakdown,
            )

            breakdown_v3 = ScoreBreakdownV3(
                semantic_score=s_semantic,
                collaborative_score=s_collab,
                content_v1_score=s_content,
                has_user_embedding=has_semantic,
                v2_breakdown=breakdown_v2,
            )

            v3_items.append(
                RecommendationV3Item(
                    book=book,
                    score=min(1.0, max(0.0, final_score)),
                    reason=reason,
                    algorithm_version=ALGORITHM_VERSION_V3,
                    breakdown=breakdown_v3,
                )
            )

        # Ordenar por score v3 descendente
        v3_items.sort(key=lambda x: (x.score, x.book.average_rating or 0.0), reverse=True)

        # Fallback Cold Start si no se alcanza el límite requerido
        if len(v3_items) < limit:
            existing_ids = {it.book.id for it in v3_items} | profile_v1.excluded_book_ids
            needed = limit - len(v3_items)
            fallback_books = (
                Book.objects.exclude(id__in=existing_ids)
                .annotate(num_readers=Count('user_entries'))
                .order_by('-average_rating', '-num_readers')[:needed]
            )
            for fb in fallback_books:
                fb_item = RecommendationV3Item(
                    book=fb,
                    score=0.10,
                    reason="Lectura destacada de la comunidad para iniciar tu viaje literario",
                    algorithm_version=ALGORITHM_VERSION_V3,
                    breakdown=ScoreBreakdownV3(
                        semantic_score=0.0,
                        collaborative_score=0.0,
                        content_v1_score=0.10,
                        has_user_embedding=False,
                    ),
                )
                v3_items.append(fb_item)

        results = [item.to_dict(request=request) for item in v3_items[:limit]]
        cache.set(cache_key, results, timeout=TTL_RECOMMENDATIONS)
        return results


def recommend_books_v3(
    user,
    limit: int = 10,
    weight_semantic: float = 0.45,
    weight_collab: float = 0.30,
    weight_content: float = 0.25,
    request=None,
) -> list[dict[str, Any]]:
    """Función de conveniencia para invocar el motor de recomendaciones v3."""
    engine = RecommendationEngineV3(
        weight_semantic=weight_semantic,
        weight_collab=weight_collab,
        weight_content=weight_content,
    )
    return engine.recommend(user=user, limit=limit, request=request)


def get_user_preference_vector(user) -> UserPreferenceVector:
    """Obtiene la metadata y vector de preferencias del usuario."""
    engine = RecommendationEngineV3()
    pref = engine.compute_user_preference_embedding(user)
    if not pref:
        return UserPreferenceVector(vector=None, dimension=0, books_count=0, weights_sum=0.0)
    return pref

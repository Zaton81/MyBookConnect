"""
Motor de Recomendaciones v2 para MyBookConnect.

Fase 50 del Roadmap: Filtrado colaborativo basado en usuarios con gustos similares
(User-User Similarity / Collaborative Filtering):
    Usuario Objetivo -> Usuarios con gustos similares -> Libros que el objetivo no ha leído -> Ranking v2

Fórmula de afinidad colaborativa:
    sim(U, V) = alpha * Jaccard(Books_U, Books_V) + (1 - alpha) * RatingCorrelation(U, V)

Puntuación de libros candidatos:
    S_collab(B) = sum(sim(U, V) * rating_norm(V, B)) / sum(sim(U, V))

Fusión híbrida v2:
    score_v2 = (1 - beta) * score_v1 + beta * S_collab

Versión del algoritmo: 'v2'
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.db.models import Count

from books.cache_utils import TTL_RECOMMENDATIONS, user_recommendations_key
from books.media_utils import build_media_url
from books.models import Book, ReadingStatus, UserBook
from books.services.recommendation_v1_service import (
    RecommendationEngineV1,
    ScoreBreakdownV1,
)

logger = logging.getLogger(__name__)

ALGORITHM_VERSION_V2 = "v2"


@dataclass
class SimilarUserPeer:
    """Representa a un lector con gustos similares al usuario objetivo."""
    user_id: int
    username: str
    similarity_score: float
    shared_books_count: int
    avatar_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'similarity_score': round(self.similarity_score, 4),
            'shared_books_count': self.shared_books_count,
            'avatar_url': self.avatar_url,
        }


@dataclass
class ScoreBreakdownV2:
    collaborative_score: float = 0.0
    content_v1_score: float = 0.0
    shared_peer_count: int = 0
    top_peer_username: str | None = None
    v1_breakdown: ScoreBreakdownV1 = field(default_factory=ScoreBreakdownV1)

    def to_dict(self) -> dict[str, Any]:
        res = {
            'collaborative': round(self.collaborative_score, 4),
            'content_v1': round(self.content_v1_score, 4),
            'shared_peers': self.shared_peer_count,
            'top_peer': self.top_peer_username,
        }
        res.update(self.v1_breakdown.to_dict())
        return res


@dataclass
class RecommendationV2Item:
    book: Book
    score: float
    reason: str
    algorithm_version: str = ALGORITHM_VERSION_V2
    breakdown: ScoreBreakdownV2 = field(default_factory=ScoreBreakdownV2)
    explanation: dict[str, Any] | None = None

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
            'explanation': self.explanation,
            'categories': [{'id': c.id, 'name': c.name} for c in b.categories.all()],
        }


class RecommendationEngineV2:
    """
    Motor de Recomendaciones v2: Filtrado colaborativo Usuario-Usuario (User-User Similarity)
    fusionado con el motor canónico de contenidos v1.
    """

    def __init__(self, collaborative_weight: float = 0.50):
        self.collaborative_weight = max(0.0, min(1.0, float(collaborative_weight)))
        self.engine_v1 = RecommendationEngineV1()

    def compute_user_similarity(self, user_a_books: dict[int, float], user_b_books: dict[int, float]) -> tuple[float, int]:
        """
        Calcula el coeficiente de afinidad lectora entre dos usuarios en escala [0, 1]
        a partir de sus libros comunes y la congruencia en sus calificaciones.
        """
        set_a = set(user_a_books.keys())
        set_b = set(user_b_books.keys())

        common_ids = set_a.intersection(set_b)
        if not common_ids:
            return 0.0, 0

        # 1. Coeficiente de Jaccard sobre catálogo compartido
        total_unique = len(set_a.union(set_b))
        jaccard = len(common_ids) / total_unique if total_unique > 0 else 0.0

        # 2. Correlación y cercanía de calificaciones en libros comunes
        rating_diffs = []
        for bid in common_ids:
            ra = user_a_books[bid]
            rb = user_b_books[bid]
            # Si ambos tienen valoración numérica (> 0)
            if ra > 0 and rb > 0:
                diff = abs(ra - rb)
                rating_diffs.append(max(0.0, 1.0 - (diff / 4.0)))

        rating_sim = sum(rating_diffs) / len(rating_diffs) if rating_diffs else 0.75

        # 3. Ponderación combinada
        combined_sim = (0.55 * jaccard) + (0.45 * rating_sim)

        # Boost sutil por solidez estadística si comparten 3 o más obras
        if len(common_ids) >= 3:
            combined_sim = min(1.0, combined_sim * 1.15)

        return round(combined_sim, 4), len(common_ids)

    def find_similar_users(self, user, limit: int = 20, min_similarity: float = 0.08) -> list[SimilarUserPeer]:
        """
        Identifica a los lectores más afines (vecinos más cercanos K-NN)
        respetando las políticas de privacidad y exclusión de bloqueos.
        """
        if not user or not user.is_authenticated:
            return []

        # 1. Libros leídos o guardados por el usuario objetivo con sus calificaciones
        my_entries = UserBook.objects.filter(user=user).values('book_id', 'rating', 'status')
        my_books_map: dict[int, float] = {}
        for e in my_entries:
            bid = e['book_id']
            rat = float(e['rating']) if e['rating'] else (4.0 if e['status'] == ReadingStatus.READ else 3.0)
            my_books_map[bid] = rat

        if not my_books_map:
            return []

        my_book_ids = set(my_books_map.keys())

        # 2. Usuarios con al menos un libro en común filtrados por privacidad y bloqueo bidireccional
        from users.policies import filter_visible_user_books
        candidate_user_books = filter_visible_user_books(
            user,
            UserBook.objects.filter(book_id__in=my_book_ids).exclude(user=user)
        )
        candidate_user_ids = (
            candidate_user_books
            .values_list('user_id', flat=True)
            .distinct()[:200]
        )

        if not candidate_user_ids:
            return []

        # Obtener entradas de los candidatos agrupadas asegurando visibilidad
        candidate_entries = (
            filter_visible_user_books(
                user,
                UserBook.objects.filter(user_id__in=candidate_user_ids)
            )
            .select_related('user')
            .values('user_id', 'user__username', 'book_id', 'rating', 'status')
        )

        users_books_map: dict[int, dict[int, float]] = defaultdict(dict)
        usernames_map: dict[int, str] = {}
        for e in candidate_entries:
            uid = e['user_id']
            usernames_map[uid] = e['user__username']
            bid = e['book_id']
            rat = float(e['rating']) if e['rating'] else (4.0 if e['status'] == ReadingStatus.READ else 3.0)
            users_books_map[uid][bid] = rat

        peers: list[SimilarUserPeer] = []
        for uid, their_books_map in users_books_map.items():
            sim, shared_count = self.compute_user_similarity(my_books_map, their_books_map)
            if sim >= min_similarity:
                peers.append(
                    SimilarUserPeer(
                        user_id=uid,
                        username=usernames_map.get(uid, f"usuario_{uid}"),
                        similarity_score=sim,
                        shared_books_count=shared_count,
                    )
                )

        peers.sort(key=lambda p: (p.similarity_score, p.shared_books_count), reverse=True)
        return peers[:limit]

    def get_collaborative_candidate_scores(
        self,
        user,
        similar_peers: list[SimilarUserPeer],
    ) -> dict[int, dict[str, Any]]:
        """
        Extrae y califica los libros leídos o valorados por lectores similares
        que el usuario objetivo aún no tiene en su biblioteca.
        """
        if not similar_peers:
            return {}

        peer_sim_map = {p.user_id: p.similarity_score for p in similar_peers}
        peer_name_map = {p.user_id: p.username for p in similar_peers}

        excluded_ids = set(UserBook.objects.filter(user=user).values_list('book_id', flat=True))

        # Libros recomendados por los vecinos similares
        peer_entries = (
            UserBook.objects.filter(user_id__in=list(peer_sim_map.keys()))
            .exclude(book_id__in=excluded_ids)
            .select_related('book')
        )

        book_weighted_sum: dict[int, float] = defaultdict(float)
        book_sim_sum: dict[int, float] = defaultdict(float)
        book_top_peers: dict[int, list[str]] = defaultdict(list)

        for entry in peer_entries:
            b_id = entry.book_id
            sim = peer_sim_map.get(entry.user_id, 0.0)

            # Peso según calificación del vecino o estado
            if entry.rating and entry.rating >= 4:
                val = entry.rating / 5.0
            elif entry.status == ReadingStatus.READ:
                val = 0.85
            elif entry.status in (ReadingStatus.READING, ReadingStatus.WANT_TO_READ):
                val = 0.65
            else:
                val = 0.40

            book_weighted_sum[b_id] += (sim * val)
            book_sim_sum[b_id] += sim

            uname = peer_name_map.get(entry.user_id)
            if uname and uname not in book_top_peers[b_id]:
                book_top_peers[b_id].append(uname)

        collaborative_results: dict[int, dict[str, Any]] = {}
        for b_id, w_sum in book_weighted_sum.items():
            s_sum = book_sim_sum[b_id]
            raw_score = w_sum / s_sum if s_sum > 0 else 0.0
            collaborative_results[b_id] = {
                'score': min(1.0, raw_score),
                'peers': book_top_peers[b_id],
                'peers_count': len(book_top_peers[b_id]),
            }

        return collaborative_results

    def recommend(
        self,
        user,
        limit: int = 10,
        request=None,
    ) -> list[dict[str, Any]]:
        """
        Genera el listado ordenado de recomendaciones v2:
        Combina la afinidad colaborativa (User-User similarity) con el motor de contenidos v1.
        """
        if not user or not user.is_authenticated:
            return []

        cache_key = user_recommendations_key(user.id, strategy='v2')
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # 1. Obtener vecinos similares
        similar_peers = self.find_similar_users(user=user, limit=20)

        # 2. Extraer candidatos colaborativos
        collab_candidates = self.get_collaborative_candidate_scores(user=user, similar_peers=similar_peers)

        # 3. Perfil de contenidos canónico v1 para scoring de base
        profile_v1 = self.engine_v1.compute_user_profile(user)

        # Libros candidatos: unión de candidatos colaborativos + catálogo viable
        candidate_ids = set(collab_candidates.keys())
        if len(candidate_ids) < 50:
            extra_ids = (
                Book.objects.exclude(id__in=profile_v1.excluded_book_ids)
                .values_list('id', flat=True)[:100]
            )
            candidate_ids.update(extra_ids)

        candidate_books = (
            Book.objects.filter(id__in=candidate_ids)
            .exclude(id__in=profile_v1.excluded_book_ids)
            .select_related('author')
            .prefetch_related('categories')
        )

        beta = self.collaborative_weight if similar_peers else 0.0

        v2_items: list[RecommendationV2Item] = []
        for book in candidate_books:
            # Puntuación v1 (contenido)
            v1_item = self.engine_v1.score_candidate(book, profile_v1)
            content_score = v1_item.score

            # Puntuación colaborativa
            collab_data = collab_candidates.get(book.id)
            if collab_data:
                collab_score = collab_data['score']
                peers_list = collab_data['peers']
                peers_count = collab_data['peers_count']
            else:
                collab_score = 0.0
                peers_list = []
                peers_count = 0

            # Fusión híbrida v2
            if similar_peers and collab_score > 0:
                final_score = (beta * collab_score) + ((1.0 - beta) * content_score)
                top_peer = peers_list[0] if peers_list else None
                if peers_count == 1:
                    reason = f"Leído y recomendado por un lector con gustos muy similares a los tuyos (@{top_peer})"
                else:
                    reason = f"Muy popular entre lectores con gustos similares a los tuyos (@{top_peer} y {peers_count - 1} más)"
            else:
                final_score = content_score
                top_peer = None
                reason = v1_item.reason

            breakdown_v2 = ScoreBreakdownV2(
                collaborative_score=collab_score,
                content_v1_score=content_score,
                shared_peer_count=peers_count,
                top_peer_username=top_peer,
                v1_breakdown=v1_item.breakdown,
            )

            v2_items.append(
                RecommendationV2Item(
                    book=book,
                    score=min(1.0, max(0.0, final_score)),
                    reason=reason,
                    algorithm_version=ALGORITHM_VERSION_V2,
                    breakdown=breakdown_v2,
                )
            )

        # Ordenar por score v2 descendente
        v2_items.sort(key=lambda x: (x.score, x.book.average_rating or 0.0), reverse=True)

        # Fallback Cold Start si no se alcanza el límite requerido
        if len(v2_items) < limit:
            existing_ids = {it.book.id for it in v2_items} | profile_v1.excluded_book_ids
            needed = limit - len(v2_items)
            fallback_books = (
                Book.objects.exclude(id__in=existing_ids)
                .annotate(num_readers=Count('user_entries'))
                .order_by('-average_rating', '-num_readers')[:needed]
            )
            for fb in fallback_books:
                fb_item = RecommendationV2Item(
                    book=fb,
                    score=0.10,
                    reason="Lectura destacada de la comunidad para iniciar tu viaje literario",
                    algorithm_version=ALGORITHM_VERSION_V2,
                    breakdown=ScoreBreakdownV2(
                        collaborative_score=0.0,
                        content_v1_score=0.10,
                        shared_peer_count=0,
                        v1_breakdown=ScoreBreakdownV1(rating=min(1.0, (fb.average_rating or 3.5) / 5.0)),
                    ),
                )
                v2_items.append(fb_item)

        from books.services.recommendation_explanation_service import explain_recommendation
        for item in v2_items[:limit]:
            expl = explain_recommendation(
                user=user,
                book=item.book,
                breakdown=item.breakdown.to_dict(),
                algorithm_version=ALGORITHM_VERSION_V2,
                existing_reason=item.reason,
            )
            item.explanation = expl
            if expl.get('primary_reason'):
                item.reason = expl['primary_reason']

        results = [item.to_dict(request=request) for item in v2_items[:limit]]
        cache.set(cache_key, results, timeout=TTL_RECOMMENDATIONS)
        return results


def recommend_books_v2(user, limit: int = 10, collaborative_weight: float = 0.50, request=None) -> list[dict[str, Any]]:
    """Función de conveniencia para invocar el motor de recomendaciones v2."""
    engine = RecommendationEngineV2(collaborative_weight=collaborative_weight)
    return engine.recommend(user=user, limit=limit, request=request)


def get_similar_readers_v2(user, limit: int = 10) -> list[dict[str, Any]]:
    """Devuelve la lista de usuarios lectores más similares al usuario objetivo."""
    engine = RecommendationEngineV2()
    peers = engine.find_similar_users(user=user, limit=limit)
    return [p.to_dict() for p in peers]

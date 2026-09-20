"""
Servicio del Feed Inteligente (Smart Feed Engine) - Fase 53.

Calcula la puntuación y justificación de cada actividad del feed social basándose
en 4 factores estratégicos descritos en Roadmap.md:
1. Recency (Frescura temporal): Decaimiento exponencial con media vida de 72h.
2. Relationship (Afinidad social): Ponderación de amigos seguidos, reciprocidad mutua
   e interacciones previas directas (likes y comentarios).
3. Engagement (Compromiso intrínseco): Tipo de actividad (reseñas/lecturas terminadas > adiciones)
   y tracción comunitaria (likes y comentarios recibidos en la reseña).
4. Content Relevance (Relevancia de contenido): Coincidencia con géneros favoritos del lector,
   afinidad de autor y presencia en la lista de deseos (wishlist).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.utils import timezone

from books.models import ReadingStatus, ReviewComment, ReviewLike, UserBook
from users.models import Activity, ActivityType

User = get_user_model()


@dataclass
class UserFeedContext:
    """Contexto precargado del usuario observador para evaluar eficientemente las actividades."""

    user_id: int
    following_ids: set[int] = field(default_factory=set)
    mutual_following_ids: set[int] = field(default_factory=set)
    interacted_user_ids: set[int] = field(default_factory=set)
    wishlist_book_ids: set[int] = field(default_factory=set)
    top_category_ids: set[int] = field(default_factory=set)
    top_author_ids: set[int] = field(default_factory=set)


class SmartFeedRankingEngine:
    """Motor de ponderación y ordenación inteligente del feed social."""

    # Pesos canónicos de los 4 factores (Suma = 1.0)
    WEIGHT_RECENCY: float = 0.30
    WEIGHT_RELATIONSHIP: float = 0.25
    WEIGHT_ENGAGEMENT: float = 0.25
    WEIGHT_RELEVANCE: float = 0.20

    # Ponderaciones intrínsecas por tipo de actividad
    ACTIVITY_TYPE_WEIGHTS: dict[str, float] = {
        ActivityType.REVIEW_CREATED: 0.90,
        ActivityType.BOOK_FINISHED: 0.85,
        ActivityType.BOOK_RATED: 0.70,
        ActivityType.LIST_CREATED: 0.65,
        ActivityType.BOOK_STARTED: 0.50,
        ActivityType.BOOK_ADDED: 0.40,
        ActivityType.USER_FOLLOWED: 0.30,
    }

    def build_user_context(self, user) -> UserFeedContext:
        """Precarga en memoria el contexto relacional y de preferencias del lector."""
        if not user or not user.is_authenticated:
            return UserFeedContext(user_id=0)

        following_ids = set(user.following.values_list('id', flat=True))
        followers_ids = set(user.followers.values_list('id', flat=True))
        mutual_ids = following_ids & followers_ids

        # Interacciones en los últimos 30 días (likes en reseñas o comentarios de usuarios seguidos)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        liked_author_ids = set(
            ReviewLike.objects.filter(
                user=user,
                created_at__gte=thirty_days_ago,
                review__user_id__in=following_ids,
            ).values_list('review__user_id', flat=True)
        )
        commented_author_ids = set(
            ReviewComment.objects.filter(
                user=user,
                created_at__gte=thirty_days_ago,
                review__user_id__in=following_ids,
            ).values_list('review__user_id', flat=True)
        )
        interacted_user_ids = liked_author_ids | commented_author_ids

        # Libros en lista de deseos del usuario
        wishlist_ids = set(
            UserBook.objects.filter(
                user=user,
            )
            .filter(wishlist=True)
            .values_list('book_id', flat=True)
        ) | set(
            UserBook.objects.filter(
                user=user,
                status=ReadingStatus.WANT_TO_READ,
            ).values_list('book_id', flat=True)
        )

        # Categorías y autores preferidos (a partir de lecturas completadas o con nota >= 4)
        positive_books = (
            UserBook.objects.filter(user=user)
            .filter(status=ReadingStatus.READ)
            .select_related('book')
            .prefetch_related('book__categories')
        )
        top_cats: set[int] = set()
        top_authors: set[int] = set()
        for ub in positive_books[:50]:
            if ub.book:
                if ub.book.author_id:
                    top_authors.add(ub.book.author_id)
                for c in ub.book.categories.all():
                    top_cats.add(c.id)

        return UserFeedContext(
            user_id=user.id,
            following_ids=following_ids,
            mutual_following_ids=mutual_ids,
            interacted_user_ids=interacted_user_ids,
            wishlist_book_ids=wishlist_ids,
            top_category_ids=top_cats,
            top_author_ids=top_authors,
        )

    def compute_score(
        self,
        activity: Activity,
        ctx: UserFeedContext,
        now=None,
    ) -> tuple[float, str]:
        """
        Calcula la puntuación multi-factor normalizada (0.0 a 1.0) y la señal explicativa del feed.
        """
        if now is None:
            now = timezone.now()

        # 1. Recency (Frescura temporal con media vida de 72 horas)
        delta = now - activity.created_at
        hours_ago = max(0.0, delta.total_seconds() / 3600.0)
        # Decaimiento exponencial: a las 72 horas vale ~0.368, a las 24 horas ~0.716
        s_recency = math.exp(-hours_ago / 72.0)

        # 2. Relationship (Afinidad social)
        author_id = activity.user_id
        s_rel = 0.20  # Base estándar para usuarios visibles
        is_mutual = False
        is_interacted = False

        if author_id == ctx.user_id:
            s_rel = 0.50
        else:
            if author_id in ctx.following_ids:
                s_rel += 0.40
            if author_id in ctx.mutual_following_ids:
                s_rel += 0.25
                is_mutual = True
            if author_id in ctx.interacted_user_ids:
                s_rel += 0.15
                is_interacted = True
        s_relationship = min(1.0, max(0.0, s_rel))

        # 3. Engagement (Compromiso del evento y tracción comunitaria)
        base_eng = self.ACTIVITY_TYPE_WEIGHTS.get(activity.type, 0.40)
        social_traction = 0.0
        has_featured_review = False

        if activity.review_id and activity.review:
            # Likes en la reseña
            likes_count = (
                activity.review.likes.count()
                if hasattr(activity.review, 'likes')
                else 0
            )
            # Comentarios en la reseña
            comments_count = (
                activity.review.comments.count()
                if hasattr(activity.review, 'comments')
                else 0
            )
            social_traction = min(0.30, likes_count * 0.05) + min(0.30, comments_count * 0.10)
            if (likes_count + comments_count) >= 3 or (activity.review.text and len(activity.review.text) > 120):
                has_featured_review = True

        s_engagement = min(1.0, base_eng + social_traction)

        # 4. Content Relevance (Relevancia de contenido para el lector)
        s_rel_content = 0.10
        is_in_wishlist = False
        is_fav_genre = False
        is_fav_author = False

        if activity.book_id and activity.book:
            b = activity.book
            if b.id in ctx.wishlist_book_ids:
                s_rel_content += 0.50
                is_in_wishlist = True
            if b.author_id and b.author_id in ctx.top_author_ids:
                s_rel_content += 0.25
                is_fav_author = True
            # Géneros compartidos
            book_cats = {c.id for c in b.categories.all()} if hasattr(b, 'categories') else set()
            if book_cats & ctx.top_category_ids:
                s_rel_content += 0.35
                is_fav_genre = True
            if (b.average_rating or 0.0) >= 4.0:
                s_rel_content += 0.10

        s_content_relevance = min(1.0, s_rel_content)

        # Puntuación final ponderada
        final_score = (
            (self.WEIGHT_RECENCY * s_recency)
            + (self.WEIGHT_RELATIONSHIP * s_relationship)
            + (self.WEIGHT_ENGAGEMENT * s_engagement)
            + (self.WEIGHT_RELEVANCE * s_content_relevance)
        )
        final_score = round(min(1.0, max(0.0, final_score)), 4)

        # Determinación de la señal explicativa principal
        if is_in_wishlist:
            feed_signal = "De tu lista de deseos"
        elif has_featured_review:
            feed_signal = "Reseña destacada"
        elif is_mutual:
            feed_signal = "Amistad mutua"
        elif is_fav_genre:
            feed_signal = "En tus géneros favoritos"
        elif is_fav_author:
            feed_signal = "De tus autores predilectos"
        elif is_interacted:
            feed_signal = "Con quien interactúas a menudo"
        elif hours_ago <= 12:
            feed_signal = "Actividad muy reciente"
        elif activity.type == ActivityType.BOOK_FINISHED:
            feed_signal = "Lectura completada"
        else:
            feed_signal = "Actividad de tu red"

        return final_score, feed_signal

    def rank_activities(
        self,
        user,
        activities: list[Activity] | Any,
        mode: str = "smart",
    ) -> list[Activity]:
        """
        Ordena y anota las actividades según el modo solicitado ('smart' o 'chronological').
        Retorna la lista de actividades enriquecidas con score y feed_signal.
        """
        activity_list = list(activities)
        if not activity_list:
            return []

        ctx = self.build_user_context(user)
        now = timezone.now()

        scored_items: list[tuple[float, Activity, str]] = []
        for act in activity_list:
            score, signal = self.compute_score(act, ctx, now=now)
            # Guardamos los atributos calculados en la instancia
            act.score = score
            act.feed_signal = signal
            scored_items.append((score, act, signal))

        if mode == "chronological":
            activity_list.sort(key=lambda a: a.created_at, reverse=True)
            return activity_list

        # Modo 'smart' por defecto: ordenar por score descendente y secundariamente por created_at
        scored_items.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return [item[1] for item in scored_items]


def get_smart_feed(user, activities_queryset, mode: str = "smart") -> list[Activity]:
    """Función de conveniencia para ordenar un queryset de actividades con el motor Smart Feed."""
    engine = SmartFeedRankingEngine()
    return engine.rank_activities(user=user, activities=activities_queryset, mode=mode)

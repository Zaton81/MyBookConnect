"""
Servicio de Tendencias y Ranking Ponderado con Decaimiento Temporal (Fase 23).

Este módulo implementa el algoritmo de puntuación temporal de popularidad para libros:
- Considera variables vivas de interacción social: nuevas reseñas, lecturas finalizadas/en curso,
  adiciones a listas de deseos, likes y comentarios.
- Modula la puntuación mediante ventanas temporales discretas ('week', 'month', 'year', 'all').
- Aplica pesos diferenciales por tipo de actividad.
- Emplea agregaciones optimizadas en PostgreSQL y almacenamiento en caché Redis (TTL: 15 min).
- Resuelve portadas con utilidades centralizadas (`build_media_url`).
"""

import logging
from datetime import timedelta
from typing import Any

from django.core.cache import cache
from django.db.models import Count, FloatField, Q, Value
from django.db.models.expressions import F
from django.db.models.functions import Coalesce
from django.utils import timezone

from books.cache_utils import TTL_TRENDING, trending_key
from books.media_utils import build_media_url
from books.models import Book

logger = logging.getLogger(__name__)

# Ventanas temporales en días
PERIOD_DAYS = {
    'week': 7,
    'month': 30,
    'year': 365,
    'all': None,
}

# Ponderaciones por tipo de actividad social
WEIGHT_REVIEW = 5.0
WEIGHT_READING = 3.0
WEIGHT_WISHLIST = 2.0
WEIGHT_LIKE = 1.5
WEIGHT_COMMENT = 1.0


def get_trending_books(
    period: str = 'week',
    limit: int = 12,
    request: Any = None,
) -> list[dict[str, Any]]:
    """
    Obtiene el listado ordenado de libros en tendencia para el periodo especificado,
    utilizando caché Redis para garantizar tiempos de respuesta menores a 20ms.

    Parámetros:
        period (str): Ventana temporal ('week', 'month', 'year', 'all'). Por defecto 'week'.
        limit (int): Cantidad máxima de libros a retornar. Por defecto 12.
        request (HttpRequest, opcional): Objeto HttpRequest para resolver URLs absolutas.

    Retorna:
        list[dict[str, Any]]: Lista de libros ordenada por puntuación de tendencia con rank,
                              totales de lectores, reseñas y score.
    """
    clean_period = period.lower().strip() if period and period.lower().strip() in PERIOD_DAYS else 'week'
    cache_key = trending_key(clean_period)

    cached_results = cache.get(cache_key)
    if cached_results is not None:
        return [
            {
                **item,
                'cover': build_media_url(item.get('cover_path') or item.get('cover'), request=request),
            }
            for item in cached_results[:limit]
        ]

    days = PERIOD_DAYS[clean_period]
    cutoff = timezone.now() - timedelta(days=days) if days else None

    # Filtros condicionales según la ventana temporal
    if cutoff:
        q_reviews = Q(reviews__created_at__gte=cutoff)
        q_readings = Q(user_entries__updated_at__gte=cutoff)
        q_wishlist = Q(user_entries__wishlist=True, user_entries__updated_at__gte=cutoff)
        q_likes = Q(reviews__likes__created_at__gte=cutoff)
        q_comments = Q(reviews__comments__created_at__gte=cutoff, reviews__comments__deleted_at__isnull=True)
    else:
        q_reviews = Q()
        q_readings = Q()
        q_wishlist = Q(user_entries__wishlist=True)
        q_likes = Q()
        q_comments = Q(reviews__comments__deleted_at__isnull=True)

    # Anotación y cómputo de señales de actividad
    trending_qs = (
        Book.objects.annotate(
            recent_reviews_count=Count('reviews', filter=q_reviews, distinct=True),
            recent_readings_count=Count('user_entries', filter=q_readings, distinct=True),
            recent_wishlists_count=Count('user_entries', filter=q_wishlist, distinct=True),
            recent_likes_count=Count('reviews__likes', filter=q_likes, distinct=True),
            recent_comments_count=Count('reviews__comments', filter=q_comments, distinct=True),
            all_time_readers=Count('user_entries', distinct=True),
            all_time_reviews=Count('reviews', distinct=True),
        )
        .annotate(
            trending_score=(
                F('recent_reviews_count') * WEIGHT_REVIEW
                + F('recent_readings_count') * WEIGHT_READING
                + F('recent_wishlists_count') * WEIGHT_WISHLIST
                + F('recent_likes_count') * WEIGHT_LIKE
                + F('recent_comments_count') * WEIGHT_COMMENT
                + Coalesce(F('average_rating'), Value(0.0), output_field=FloatField()) * 0.5
            )
        )
        .select_related('author')
        .order_by(
            '-trending_score',
            '-all_time_readers',
            '-average_rating',
            '-created_at',
        )[:limit]
    )

    cached_items: list[dict[str, Any]] = []
    for rank, book in enumerate(trending_qs, start=1):
        score_val = getattr(book, 'trending_score', 0.0)
        cached_items.append({
            'rank': rank,
            'id': book.id,
            'title': book.title,
            'cover_path': book.cover.url if book.cover else None,
            'author_name': book.author.name if book.author else '',
            'average_rating': book.average_rating,
            'readers_count': book.all_time_readers,
            'reviews_count': book.all_time_reviews,
            'trending_score': round(float(score_val), 1) if score_val else 0.0,
            'period': clean_period,
        })

    try:
        cache.set(cache_key, cached_items, timeout=TTL_TRENDING)
    except Exception as exc:
        logger.warning(f"Error guardando tendencias ({clean_period}) en caché: {exc}")

    return [
        {
            **item,
            'cover': build_media_url(item.get('cover_path'), request=request),
        }
        for item in cached_items
    ]

"""
Servicio de Estadísticas de Lectura (Fase 22).

Este módulo proporciona el cálculo eficiente y agregado de métricas de lectura de un usuario:
- Cantidad de libros por estado (leídos, en progreso, quiero leer, abandonados).
- Total de páginas leídas.
- Calificación media y distribución de valoraciones (1 a 10).
- Top 5 géneros más leídos con porcentaje y conteo.
- Top 5 autores con más libros leídos.
- Evolución mensual de libros terminados en los últimos 12 meses.
- Libros terminados durante el año actual.

Incluye estrategia de caché Redis con TTL de 15 minutos e invalidación atómica.
"""

import calendar
import logging
from datetime import date
from typing import Any

from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from books.cache_utils import TTL_STATS, user_stats_key
from books.models import Author, Category, ReadingStatus, Review, UserBook

logger = logging.getLogger(__name__)


def get_user_reading_stats(user_id: int) -> dict[str, Any]:
    """
    Obtiene las estadísticas agregadas de lectura de un usuario,
    utilizando caché Redis para evitar cómputos costosos en cada petición.

    Parámetros:
        user_id (int): Identificador del usuario.

    Retorna:
        dict[str, Any]: Diccionario estructurado con KPIs, distribuciones y rankings.
    """
    cache_key = user_stats_key(user_id)
    cached_stats = cache.get(cache_key)
    if cached_stats is not None:
        return cached_stats

    # QuerySet base para las lecturas del usuario
    user_books = UserBook.objects.filter(user_id=user_id)
    total_books = user_books.count()

    # Libros leídos o marcados como finalizados
    read_books = user_books.filter(Q(status=ReadingStatus.READ) | Q(is_read=True))
    total_read = read_books.count()

    # Libros actualmente en progreso
    currently_reading = user_books.filter(status=ReadingStatus.READING).count()

    # Libros en lista de deseos o pendientes de leer
    want_to_read = user_books.filter(Q(status=ReadingStatus.WANT_TO_READ) | Q(wishlist=True)).count()

    # Libros abandonados
    abandoned = user_books.filter(status=ReadingStatus.ABANDONED).count()

    # Páginas leídas (suma de current_page en la biblioteca del usuario)
    pages_agg = user_books.aggregate(total_pages=Sum('current_page'))['total_pages']
    total_pages_read = int(pages_agg) if pages_agg else 0

    # Calificación promedio: de reseñas o del rating en UserBook
    avg_rating = None
    review_avg = Review.objects.filter(user_id=user_id, rating__isnull=False).aggregate(avg=Avg('rating'))['avg']
    if review_avg is not None:
        avg_rating = round(float(review_avg), 2)
    else:
        ub_avg = user_books.filter(rating__isnull=False).aggregate(avg=Avg('rating'))['avg']
        if ub_avg is not None:
            avg_rating = round(float(ub_avg), 2)

    # Distribución de calificaciones (1 a 10)
    ratings_distribution = {i: 0 for i in range(1, 11)}
    review_ratings = (
        Review.objects.filter(user_id=user_id, rating__isnull=False)
        .values('rating')
        .annotate(count=Count('id'))
    )
    if review_ratings:
        for item in review_ratings:
            r = item['rating']
            if 1 <= r <= 10:
                ratings_distribution[r] = item['count']
    else:
        ub_ratings = (
            user_books.filter(rating__isnull=False)
            .values('rating')
            .annotate(count=Count('id'))
        )
        for item in ub_ratings:
            r = item['rating']
            if 1 <= r <= 10:
                ratings_distribution[r] = item['count']

    # Top géneros (basados en libros leídos o en todos los libros guardados)
    target_entries = read_books if read_books.exists() else user_books
    top_categories_qs = (
        Category.objects.filter(books__user_entries__in=target_entries)
        .values('name')
        .annotate(count=Count('books', distinct=True))
        .order_by('-count')[:5]
    )
    total_genre_occurrences = sum(c['count'] for c in top_categories_qs) or 1
    top_genres = [
        {
            'name': cat['name'],
            'count': cat['count'],
            'percentage': round((cat['count'] / total_genre_occurrences) * 100, 1),
        }
        for cat in top_categories_qs
    ]

    # Top autores (basados en libros leídos o en todos los libros guardados)
    top_authors_qs = (
        Author.objects.filter(books__user_entries__in=target_entries)
        .values('id', 'name')
        .annotate(count=Count('books', distinct=True))
        .order_by('-count')[:5]
    )
    top_authors = [
        {
            'id': auth['id'],
            'name': auth['name'],
            'count': auth['count'],
        }
        for auth in top_authors_qs
    ]

    # Libros leídos en el año actual
    now = timezone.now()
    current_year = now.year
    books_this_year = read_books.filter(
        Q(finished_at__year=current_year)
        | Q(finished_at__isnull=True, updated_at__year=current_year)
    ).count()

    # Libros por mes en los últimos 12 meses
    books_per_month = []
    # Generar tuplas (año, mes) para los últimos 12 meses en orden cronológico
    year_month_list = []
    for i in range(11, -1, -1):
        target_month = now.month - i
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        year_month_list.append((target_year, target_month))

    for y, m in year_month_list:
        month_label = f"{y}-{m:02d}"
        month_name = calendar.month_abbr[m]
        count = read_books.filter(
            Q(finished_at__year=y, finished_at__month=m)
            | Q(finished_at__isnull=True, updated_at__year=y, updated_at__month=m)
        ).count()
        books_per_month.append({
            'key': month_label,
            'label': f"{month_name} {y}",
            'count': count,
        })

    stats = {
        'total_books': total_books,
        'total_read': total_read,
        'currently_reading': currently_reading,
        'want_to_read': want_to_read,
        'abandoned': abandoned,
        'total_pages_read': total_pages_read,
        'average_rating': avg_rating,
        'ratings_distribution': ratings_distribution,
        'top_genres': top_genres,
        'top_authors': top_authors,
        'books_this_year': books_this_year,
        'books_per_month': books_per_month,
    }

    try:
        cache.set(cache_key, stats, timeout=TTL_STATS)
    except Exception as exc:
        logger.warning(f"Error guardando estadísticas de usuario {user_id} en caché: {exc}")

    return stats

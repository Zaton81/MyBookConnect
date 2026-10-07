"""
Servicio de Estadísticas Avanzadas de Lectura (Sprint 15).

Este módulo proporciona el cálculo eficiente, agregado y granular de métricas de lectura:
- Filtrado temporal flexible (año específico o histórico global).
- Catálogo de años disponibles con actividad (`available_years`).
- Métricas de ritmo y velocidad (`reading_pace`: días por libro, libro más veloz y pausado, páginas/día).
- Distribución por longitud de páginas (`length_distribution`: cortos, medios, largos, épicos).
- Desglose por formato y posesión (`format_distribution`: físico vs digital, en propiedad vs prestado).
- Evolución mensual con doble eje (libros terminados y páginas leídas por mes).
- Memoria Anual / "Year in Review" (`year_in_review`: comparativa interanual, mejor valorado, género y autor predilecto).
- KPIs de biblioteca y compatibilidad retroactiva 100%.

Incluye estrategia de caché Redis con TTL de 15 minutos e invalidación atómica.
"""

import calendar
import logging
from typing import Any

from django.core.cache import cache
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from books.cache_utils import TTL_STATS, user_stats_key
from books.models import Author, Category, ReadingStatus, Review, UserBook

logger = logging.getLogger(__name__)


def get_user_reading_stats(user_id: int, year: int | str | None = None) -> dict[str, Any]:
    """
    Obtiene las estadísticas avanzadas agregadas de lectura de un usuario.

    Parámetros:
        user_id (int): Identificador del usuario.
        year (int | str | None): Año específico a filtrar (ej. 2026, 2025) o 'all'/None para histórico.

    Retorna:
        dict[str, Any]: Diccionario estructurado con KPIs, ritmo, distribuciones, evolución mensual y retrospectiva.
    """
    # Parsear año seleccionado
    selected_year: int | None = None
    if year is not None and str(year).strip().lower() not in ('all', '', 'none'):
        try:
            selected_year = int(year)
        except (ValueError, TypeError):
            selected_year = None

    cache_key = user_stats_key(user_id, year=selected_year)
    cached_stats = cache.get(cache_key)
    if cached_stats is not None:
        return cached_stats

    now = timezone.now()
    current_year = now.year

    # QuerySet base para las lecturas del usuario con prefetch optimizado
    user_books = UserBook.objects.filter(user_id=user_id).select_related('book', 'book__author')
    total_library_books = user_books.count()

    # Obtener años disponibles con actividad para selector del frontend
    distinct_years = set()
    for finished_at, updated_at in user_books.values_list('finished_at', 'updated_at'):
        if finished_at:
            distinct_years.add(finished_at.year)
        elif updated_at:
            distinct_years.add(updated_at.year)
    if not distinct_years:
        distinct_years.add(current_year)
    available_years = sorted(list(distinct_years), reverse=True)

    # Libros leídos o marcados como finalizados en toda la historia
    all_read_books = user_books.filter(Q(status=ReadingStatus.READ) | Q(is_read=True))

    # Filtrar según el año seleccionado
    if selected_year is not None:
        read_books = all_read_books.filter(
            Q(finished_at__year=selected_year)
            | Q(finished_at__isnull=True, updated_at__year=selected_year)
        )
        total_books = read_books.count()
        total_read = read_books.count()
    else:
        read_books = all_read_books
        total_books = total_library_books
        total_read = all_read_books.count()

    # Estado actual de lectura (KPIs de biblioteca)
    currently_reading = user_books.filter(status=ReadingStatus.READING).count()
    want_to_read = user_books.filter(Q(status=ReadingStatus.WANT_TO_READ) | Q(wishlist=True)).count()
    abandoned = user_books.filter(status=ReadingStatus.ABANDONED).count()

    # Páginas leídas en el periodo o histórico global
    if selected_year is not None:
        pages_agg = read_books.aggregate(total_pages=Sum('current_page'))['total_pages']
    else:
        pages_agg = user_books.aggregate(total_pages=Sum('current_page'))['total_pages']
    total_pages_read = int(pages_agg) if pages_agg else 0

    # Calificación promedio: de reseñas o del rating en UserBook
    avg_rating = None
    target_entries_for_ratings = read_books if read_books.exists() else user_books
    book_ids_in_period = target_entries_for_ratings.values_list('book_id', flat=True)

    if selected_year is not None:
        review_avg = Review.objects.filter(
            user_id=user_id,
            book_id__in=book_ids_in_period,
            rating__isnull=False
        ).aggregate(avg=Avg('rating'))['avg']
    else:
        review_avg = Review.objects.filter(
            user_id=user_id,
            rating__isnull=False
        ).aggregate(avg=Avg('rating'))['avg']

    if review_avg is not None:
        avg_rating = round(float(review_avg), 2)
    else:
        ub_avg = target_entries_for_ratings.filter(rating__isnull=False).aggregate(avg=Avg('rating'))['avg']
        if ub_avg is not None:
            avg_rating = round(float(ub_avg), 2)

    # Distribución de calificaciones (1 a 5)
    ratings_distribution = dict.fromkeys(range(1, 6), 0)
    if selected_year is not None:
        review_ratings = (
            Review.objects.filter(user_id=user_id, book_id__in=book_ids_in_period, rating__isnull=False)
            .values('rating')
            .annotate(count=Count('id'))
        )
    else:
        review_ratings = (
            Review.objects.filter(user_id=user_id, rating__isnull=False)
            .values('rating')
            .annotate(count=Count('id'))
        )

    if review_ratings.exists():
        for item in review_ratings:
            r = item['rating']
            if 1 <= r <= 5:
                ratings_distribution[r] = item['count']
    else:
        ub_ratings = (
            target_entries_for_ratings.filter(rating__isnull=False)
            .values('rating')
            .annotate(count=Count('id'))
        )
        for item in ub_ratings:
            r = item['rating']
            if 1 <= r <= 5:
                ratings_distribution[r] = item['count']

    # Top géneros (basados en libros leídos del periodo o en toda la biblioteca)
    top_categories_qs = (
        Category.objects.filter(books__user_entries__in=target_entries_for_ratings)
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

    # Top autores
    top_authors_qs = (
        Author.objects.filter(books__user_entries__in=target_entries_for_ratings)
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

    # Libros leídos en el año actual (para compatibilidad de KPI)
    books_this_year = all_read_books.filter(
        Q(finished_at__year=current_year)
        | Q(finished_at__isnull=True, updated_at__year=current_year)
    ).count()

    # ── 1. MÉTRICAS DE RITMO Y VELOCIDAD (reading_pace) ──
    days_to_read_list: list[dict[str, Any]] = []
    for entry in read_books:
        if entry.started_at and entry.finished_at and entry.finished_at >= entry.started_at:
            duration_days = (entry.finished_at - entry.started_at).days + 1
            author_name = entry.book.get_author_names() if hasattr(entry.book, 'get_author_names') else (entry.book.author.name if entry.book.author else 'Autor desconocido')
            cover_url = entry.book.cover.url if entry.book.cover else None
            days_to_read_list.append({
                'book_id': entry.book.id,
                'title': entry.book.title,
                'author': author_name,
                'cover': cover_url,
                'days': duration_days,
                'pages': entry.current_page or 0,
            })

    avg_days_per_book: float | None = None
    fastest_book: dict[str, Any] | None = None
    slowest_book: dict[str, Any] | None = None

    if days_to_read_list:
        avg_days_per_book = round(sum(d['days'] for d in days_to_read_list) / len(days_to_read_list), 1)
        fastest_book = min(days_to_read_list, key=lambda x: x['days'])
        slowest_book = max(days_to_read_list, key=lambda x: x['days'])

    # Páginas promedio por día y mes
    if selected_year is not None:
        if selected_year == current_year:
            elapsed_days = max(now.timetuple().tm_yday, 1)
            elapsed_months = max(now.month, 1)
        elif selected_year < current_year:
            elapsed_days = 366 if calendar.isleap(selected_year) else 365
            elapsed_months = 12
        else:
            elapsed_days = 1
            elapsed_months = 1
    else:
        # Histórico: considerar los últimos 12 meses o días activos
        elapsed_days = 365
        elapsed_months = 12

    avg_pages_per_day = round(total_pages_read / elapsed_days, 1) if elapsed_days > 0 else 0.0
    avg_pages_per_month = round(total_pages_read / elapsed_months, 1) if elapsed_months > 0 else 0.0

    # ── 2. DISTRIBUCIÓN POR LONGITUD DE LIBROS (length_distribution) ──
    short_books = 0      # < 200 páginas
    medium_books = 0     # 200 - 399 páginas
    long_books = 0       # 400 - 599 páginas
    epic_books = 0       # 600+ páginas

    books_with_pages = [b for b in read_books if (b.current_page or 0) > 0]
    total_books_with_pages = len(books_with_pages)

    longest_book: dict[str, Any] | None = None
    shortest_book: dict[str, Any] | None = None

    for entry in books_with_pages:
        p = entry.current_page
        if p < 200:
            short_books += 1
        elif p < 400:
            medium_books += 1
        elif p < 600:
            long_books += 1
        else:
            epic_books += 1

    if books_with_pages:
        max_entry = max(books_with_pages, key=lambda x: x.current_page)
        min_entry = min(books_with_pages, key=lambda x: x.current_page)
        longest_book = {
            'book_id': max_entry.book.id,
            'title': max_entry.book.title,
            'author': max_entry.book.get_author_names(),
            'pages': max_entry.current_page,
            'cover': max_entry.book.cover.url if max_entry.book.cover else None,
        }
        shortest_book = {
            'book_id': min_entry.book.id,
            'title': min_entry.book.title,
            'author': min_entry.book.get_author_names(),
            'pages': min_entry.current_page,
            'cover': min_entry.book.cover.url if min_entry.book.cover else None,
        }

    denom_len = total_books_with_pages or 1
    length_distribution = {
        'short': {
            'label': 'Cortos (< 200 pág)',
            'count': short_books,
            'percentage': round((short_books / denom_len) * 100, 1),
        },
        'medium': {
            'label': 'Medios (200 - 399 pág)',
            'count': medium_books,
            'percentage': round((medium_books / denom_len) * 100, 1),
        },
        'long': {
            'label': 'Largos (400 - 599 pág)',
            'count': long_books,
            'percentage': round((long_books / denom_len) * 100, 1),
        },
        'epic': {
            'label': 'Épicos (600+ pág)',
            'count': epic_books,
            'percentage': round((epic_books / denom_len) * 100, 1),
        },
        'longest_book': longest_book,
        'shortest_book': shortest_book,
    }

    # ── 3. DISTRIBUCIÓN POR FORMATO Y POSESIÓN (format_distribution) ──
    digital_count = read_books.filter(is_digital=True).count()
    physical_count = read_books.filter(is_digital=False).count()
    owned_count = read_books.filter(owned=True).count()
    borrowed_count = read_books.filter(owned=False).count()
    total_format_denom = total_read or 1

    format_distribution = {
        'physical_count': physical_count,
        'physical_percentage': round((physical_count / total_format_denom) * 100, 1),
        'digital_count': digital_count,
        'digital_percentage': round((digital_count / total_format_denom) * 100, 1),
        'owned_count': owned_count,
        'owned_percentage': round((owned_count / total_format_denom) * 100, 1),
        'borrowed_count': borrowed_count,
        'borrowed_percentage': round((borrowed_count / total_format_denom) * 100, 1),
    }

    # ── 4. EVOLUCIÓN MENSUAL DOBLE EJE (books_per_month) ──
    books_per_month: list[dict[str, Any]] = []
    if selected_year is not None:
        # Los 12 meses del año seleccionado
        year_month_list = [(selected_year, m) for m in range(1, 13)]
    else:
        # Los últimos 12 meses cronológicos
        year_month_list = []
        for i in range(11, -1, -1):
            target_month = now.month - i
            target_year = now.year
            while target_month <= 0:
                target_month += 12
                target_year -= 1
            year_month_list.append((target_year, target_month))

    peak_month_label = None
    peak_month_count = -1

    for y, m in year_month_list:
        month_label = f"{y}-{m:02d}"
        month_name = calendar.month_abbr[m]
        month_qs = all_read_books.filter(
            Q(finished_at__year=y, finished_at__month=m)
            | Q(finished_at__isnull=True, updated_at__year=y, updated_at__month=m)
        )
        count = month_qs.count()
        pages_month = month_qs.aggregate(p=Sum('current_page'))['p'] or 0

        if count > peak_month_count and count > 0:
            peak_month_count = count
            peak_month_label = f"{month_name} {y}"

        books_per_month.append({
            'key': month_label,
            'label': f"{month_name} {y}",
            'month': m,
            'year': y,
            'count': count,
            'pages': int(pages_month),
        })

    highest_reading_month = {
        'label': peak_month_label or 'Sin registros suficientes',
        'count': max(peak_month_count, 0),
    }

    # ── 5. MEMORIA ANUAL / "YEAR IN REVIEW" (year_in_review) ──
    eval_year = selected_year if selected_year is not None else current_year
    prev_year = eval_year - 1

    # Libros y páginas del año anterior para comparativa interanual
    prev_year_qs = all_read_books.filter(
        Q(finished_at__year=prev_year)
        | Q(finished_at__isnull=True, updated_at__year=prev_year)
    )
    prev_year_books = prev_year_qs.count()
    prev_year_pages = prev_year_qs.aggregate(p=Sum('current_page'))['p'] or 0

    books_difference = total_read - prev_year_books if selected_year is not None else books_this_year - prev_year_books
    books_percentage_change: float | None = None
    if prev_year_books > 0:
        books_percentage_change = round((books_difference / prev_year_books) * 100, 1)

    # Libro mejor valorado en el año evaluado
    highest_rated_book: dict[str, Any] | None = None
    evaluated_read_books = read_books if selected_year is not None else all_read_books.filter(
        Q(finished_at__year=eval_year) | Q(finished_at__isnull=True, updated_at__year=eval_year)
    )

    rated_books_in_period = evaluated_read_books.filter(rating__isnull=False).order_by('-rating')
    if rated_books_in_period.exists():
        best_entry = rated_books_in_period.first()
        highest_rated_book = {
            'book_id': best_entry.book.id,
            'title': best_entry.book.title,
            'author': best_entry.book.get_author_names(),
            'rating': best_entry.rating,
            'cover': best_entry.book.cover.url if best_entry.book.cover else None,
        }

    year_in_review = {
        'year': eval_year,
        'total_books': total_read if selected_year is not None else books_this_year,
        'total_pages': total_pages_read,
        'highest_rated_book': highest_rated_book,
        'favorite_genre': top_genres[0]['name'] if top_genres else None,
        'favorite_author': top_authors[0]['name'] if top_authors else None,
        'comparison_previous_year': {
            'previous_year': prev_year,
            'previous_year_books': prev_year_books,
            'previous_year_pages': int(prev_year_pages),
            'books_difference': books_difference,
            'books_percentage_change': books_percentage_change,
        },
    }

    reading_pace = {
        'avg_days_per_book': avg_days_per_book,
        'fastest_book': fastest_book,
        'slowest_book': slowest_book,
        'avg_pages_per_day': avg_pages_per_day,
        'avg_pages_per_month': avg_pages_per_month,
        'highest_reading_month': highest_reading_month,
    }

    stats = {
        # Campos compatibles existentes
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
        # Nuevos campos avanzados (Sprint 15)
        'selected_year': selected_year,
        'available_years': available_years,
        'reading_pace': reading_pace,
        'length_distribution': length_distribution,
        'format_distribution': format_distribution,
        'year_in_review': year_in_review,
    }

    try:
        cache.set(cache_key, stats, timeout=TTL_STATS)
    except Exception as exc:
        logger.warning(f"Error guardando estadísticas de usuario {user_id} en caché: {exc}")

    return stats

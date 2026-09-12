"""
Servicio de Feedback y Analítica de Recomendaciones (Fase 25).

Permite registrar interacciones y conversiones (mostrado, clickeado, abierto,
añadido a lista de deseos, lectura iniciada, lectura finalizada, valorado)
y calcular métricas clave de rendimiento como CTR, tasas de conversión y
desgloses por versión de algoritmo y estrategia.
"""

import logging
from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from books.models import Book, RecommendationFeedback, RecommendationFeedbackAction

logger = logging.getLogger(__name__)
User = get_user_model()


def record_recommendation_event(
    user: Any,
    book_id: int,
    action: str,
    recommendation_id: str = '',
    strategy: str = 'hybrid',
    algorithm_version: str = 'v1.0',
    metadata: dict[str, Any] | None = None,
) -> RecommendationFeedback:
    """
    Registra un evento de interacción o conversión sobre una recomendación.

    :param user: Instancia del usuario autenticado que realiza la interacción.
    :param book_id: Identificador del libro objetivo.
    :param action: Tipo de evento (recommendation_shown, recommendation_clicked, etc.).
    :param recommendation_id: Identificador correlativo del lote o elemento de recomendación.
    :param strategy: Estrategia algorítmica utilizada (ej: 'hybrid', 'social', 'rules', 'item_to_item').
    :param algorithm_version: Versión del modelo/algoritmo (ej: 'v1.0').
    :param metadata: Información adicional contextual en formato dict.
    :return: Instancia creada de RecommendationFeedback.
    :raises ValueError: Si la acción no pertenece a las acciones válidas o si el libro no existe.
    """
    valid_actions = {choice[0] for choice in RecommendationFeedbackAction.choices}
    if action not in valid_actions:
        raise ValueError(
            f"Acción '{action}' inválida. Acciones permitidas: {', '.join(sorted(valid_actions))}"
        )

    try:
        book = Book.objects.get(pk=book_id)
    except Book.DoesNotExist as exc:
        raise ValueError(f"Libro con id={book_id} no encontrado.") from exc

    feedback = RecommendationFeedback.objects.create(
        user=user,
        book=book,
        action=action,
        recommendation_id=recommendation_id or '',
        strategy=strategy or 'hybrid',
        algorithm_version=algorithm_version or 'v1.0',
        metadata=metadata or {},
    )

    logger.debug(
        "Recommendation feedback registrado: user=%s, book=%s, action=%s, strategy=%s",
        user.username if hasattr(user, 'username') else user,
        book_id,
        action,
        strategy,
    )
    return feedback


def get_recommendation_metrics(
    user: Any | None = None,
    strategy: str | None = None,
    algorithm_version: str | None = None,
    days: int | None = None,
) -> dict[str, Any]:
    """
    Calcula agregados y ratios de conversión (CTR, wishlist rate, completion rate)
    para evaluar la eficacia de los algoritmos de recomendación.

    :param user: Opcional, filtrar por usuario específico (None para métricas globales).
    :param strategy: Opcional, filtrar por estrategia algorítmica ('hybrid', 'social', etc.).
    :param algorithm_version: Opcional, filtrar por versión de algoritmo ('v1.0', etc.).
    :param days: Opcional, ventana temporal en días (None para histórico completo).
    :return: Diccionario con contadores, tasas porcentuales y desgloses.
    """
    queryset = RecommendationFeedback.objects.all()

    if user is not None and getattr(user, 'is_authenticated', False):
        queryset = queryset.filter(user=user)

    if strategy:
        queryset = queryset.filter(strategy=strategy)

    if algorithm_version:
        queryset = queryset.filter(algorithm_version=algorithm_version)

    if days is not None and days > 0:
        since = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(created_at__gte=since)

    # Conteo agrupado por tipo de acción
    action_counts = dict(
        queryset.values('action')
        .annotate(total=Count('id'))
        .values_list('action', 'total')
    )

    shown = action_counts.get(RecommendationFeedbackAction.RECOMMENDATION_SHOWN, 0)
    clicked = action_counts.get(RecommendationFeedbackAction.RECOMMENDATION_CLICKED, 0)
    opened = action_counts.get(RecommendationFeedbackAction.BOOK_OPENED, 0)
    wishlist = action_counts.get(RecommendationFeedbackAction.WISHLIST_ADDED, 0)
    started = action_counts.get(RecommendationFeedbackAction.READING_STARTED, 0)
    finished = action_counts.get(RecommendationFeedbackAction.READING_FINISHED, 0)
    rated = action_counts.get(RecommendationFeedbackAction.RATED, 0)

    # Ratios (en porcentaje redondeado a 2 decimales)
    ctr = round((clicked / shown) * 100.0, 2) if shown > 0 else 0.0
    wishlist_rate = round((wishlist / shown) * 100.0, 2) if shown > 0 else 0.0
    start_rate = round((started / shown) * 100.0, 2) if shown > 0 else 0.0
    completion_rate = round((finished / started) * 100.0, 2) if started > 0 else 0.0
    rating_rate = round((rated / shown) * 100.0, 2) if shown > 0 else 0.0

    # Desglose por estrategia
    strategy_groups = (
        queryset.values('strategy')
        .annotate(
            shown_count=Count('id', filter=Q(action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN)),
            clicked_count=Count('id', filter=Q(action=RecommendationFeedbackAction.RECOMMENDATION_CLICKED)),
            wishlist_count=Count('id', filter=Q(action=RecommendationFeedbackAction.WISHLIST_ADDED)),
            started_count=Count('id', filter=Q(action=RecommendationFeedbackAction.READING_STARTED)),
            finished_count=Count('id', filter=Q(action=RecommendationFeedbackAction.READING_FINISHED)),
        )
        .order_by('-shown_count')
    )

    by_strategy = []
    for item in strategy_groups:
        s_name = item['strategy'] or 'unknown'
        s_shown = item['shown_count']
        s_clicked = item['clicked_count']
        s_ctr = round((s_clicked / s_shown) * 100.0, 2) if s_shown > 0 else 0.0
        by_strategy.append({
            'strategy': s_name,
            'shown': s_shown,
            'clicked': s_clicked,
            'ctr': s_ctr,
            'wishlist_added': item['wishlist_count'],
            'reading_started': item['started_count'],
            'reading_finished': item['finished_count'],
        })

    # Desglose por versión de algoritmo
    version_groups = (
        queryset.values('algorithm_version')
        .annotate(
            shown_count=Count('id', filter=Q(action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN)),
            clicked_count=Count('id', filter=Q(action=RecommendationFeedbackAction.RECOMMENDATION_CLICKED)),
        )
        .order_by('-shown_count')
    )

    by_version = []
    for item in version_groups:
        v_name = item['algorithm_version'] or 'unknown'
        v_shown = item['shown_count']
        v_clicked = item['clicked_count']
        v_ctr = round((v_clicked / v_shown) * 100.0, 2) if v_shown > 0 else 0.0
        by_version.append({
            'version': v_name,
            'shown': v_shown,
            'clicked': v_clicked,
            'ctr': v_ctr,
        })

    # Libros con mayor interacción positiva (clicks + conversiones)
    top_books_qs = (
        queryset.filter(action__in=[
            RecommendationFeedbackAction.RECOMMENDATION_CLICKED,
            RecommendationFeedbackAction.WISHLIST_ADDED,
            RecommendationFeedbackAction.READING_STARTED,
        ])
        .values('book_id', 'book__title')
        .annotate(interactions=Count('id'))
        .order_by('-interactions')[:10]
    )
    top_books = [
        {'book_id': b['book_id'], 'title': b['book__title'], 'interactions': b['interactions']}
        for b in top_books_qs
    ]

    return {
        'period_days': days,
        'filters': {
            'strategy': strategy,
            'algorithm_version': algorithm_version,
            'user_id': user.id if user and getattr(user, 'id', None) else None,
        },
        'totals': {
            'all_events': queryset.count(),
            'shown': shown,
            'clicked': clicked,
            'book_opened': opened,
            'wishlist_added': wishlist,
            'reading_started': started,
            'reading_finished': finished,
            'rated': rated,
        },
        'kpis': {
            'ctr': ctr,
            'wishlist_rate': wishlist_rate,
            'start_rate': start_rate,
            'completion_rate': completion_rate,
            'rating_rate': rating_rate,
        },
        'by_strategy': by_strategy,
        'by_version': by_version,
        'top_books': top_books,
    }

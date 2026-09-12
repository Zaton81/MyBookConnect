"""
Servicio del motor de recomendaciones híbrido de MyBookConnect.

Implementa:
1. Recomendaciones personalizadas para usuarios basadas en:
   - Preferencias de género e historial de lectura (35%)
   - Afinidad y valoración de autores (20%)
   - Comportamiento social y amigos seguidos (20%)
   - Similitud semántica / temática de sinopsis (15%)
   - Descubrimiento y serendipia de alta valoración (10%)
2. Explicabilidad transparente ("reasons") para cada elemento recomendado.
3. Recomendaciones contextuales Item-to-Item ("quienes leyeron X también leyeron Y").
4. Caché en Redis y soporte robusto para situaciones de 'cold start'.
"""

import logging
from collections import defaultdict

from django.core.cache import cache
from django.db.models import Count, Q

from books.cache_utils import (
    TTL_RECOMMENDATIONS,
    book_recommendations_key,
    user_recommendations_key,
)
from books.media_utils import build_media_url
from books.models import Book, Category, ReadingStatus, UserBook

logger = logging.getLogger(__name__)

# Pesos configurables por defecto para el motor híbrido
DEFAULT_WEIGHTS = {
    'genre_preferences': 0.35,
    'author_affinity': 0.20,
    'social_behavior': 0.20,
    'semantic_similarity': 0.15,
    'discovery': 0.10,
}


def _calculate_user_affinity(user) -> tuple[dict[int, float], dict[int, float], list[str]]:
    """
    Analiza el historial de lecturas del usuario para extraer afinidades ponderadas
    por categoría y autor, así como temas destacados de sus libros favoritos.
    """
    category_affinity: dict[int, float] = defaultdict(float)
    author_affinity: dict[int, float] = defaultdict(float)
    favorite_keywords: list[str] = []

    user_entries = (
        UserBook.objects.filter(user=user)
        .select_related('book', 'book__author')
        .prefetch_related('book__categories')
    )

    for entry in user_entries:
        # Ponderación según la valoración o el estado de lectura
        if entry.rating:
            weight = entry.rating / 5.0
        elif entry.status == ReadingStatus.READ:
            weight = 0.8
        elif entry.status in (ReadingStatus.READING, ReadingStatus.WANT_TO_READ):
            weight = 0.6
        else:
            weight = 0.2

        # Ponderar categorías del libro
        for cat in entry.book.categories.all():
            category_affinity[cat.id] += weight

        # Ponderar autor
        if entry.book.author_id:
            author_affinity[entry.book.author_id] += weight

        # Si fue muy valorado, recolectar palabras clave del título y sinopsis
        if (entry.rating and entry.rating >= 4) or entry.status == ReadingStatus.READ:
            tokens = [w.lower() for w in entry.book.title.split() if len(w) > 3]
            favorite_keywords.extend(tokens[:5])

    # Normalización simple para acotar a un rango comparable [0, 1]
    max_cat = max(category_affinity.values()) if category_affinity else 1.0
    for cid in category_affinity:
        category_affinity[cid] /= max_cat

    max_auth = max(author_affinity.values()) if author_affinity else 1.0
    for aid in author_affinity:
        author_affinity[aid] /= max_auth

    return category_affinity, author_affinity, favorite_keywords


def get_user_recommendations(
    user,
    limit: int = 10,
    strategy: str = 'hybrid',
    weights: dict | None = None,
    request=None,
) -> list[dict]:
    """
    Genera recomendaciones de libros personalizadas para el usuario autenticado.

    :param user: Instancia del modelo User solicitante.
    :param limit: Número máximo de libros a recomendar.
    :param strategy: Estrategia de scoring ('hybrid', 'rules', 'social', 'semantic').
    :param weights: Diccionario opcional para sobreescribir los pesos de factores.
    :param request: HttpRequest opcional para construir URLs absolutas de carátulas.
    :return: Lista de diccionarios con book, score y reason.
    """
    if not user or not user.is_authenticated:
        return []

    cache_key = user_recommendations_key(user.id, strategy)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    w = dict(DEFAULT_WEIGHTS)
    if weights and isinstance(weights, dict):
        w.update(weights)

    # 1. Libros que deben ser estrictamente excluidos (ya en biblioteca del usuario)
    excluded_book_ids = set(
        UserBook.objects.filter(user=user).values_list('book_id', flat=True)
    )

    # 2. Análisis del perfil y afinidades del usuario
    cat_affinity, auth_affinity, fav_keywords = _calculate_user_affinity(user)

    # 3. Factor social: libros leídos o valorados por personas a las que sigue
    social_book_scores: dict[int, float] = defaultdict(float)
    social_book_friends: dict[int, list[str]] = defaultdict(list)

    followed_users = list(user.following.values_list('id', flat=True))
    if hasattr(user, 'blocked_users'):
        blocked_ids = set(user.blocked_users.values_list('id', flat=True))
        followed_users = [uid for uid in followed_users if uid not in blocked_ids]

    if followed_users:
        followed_entries = (
            UserBook.objects.filter(user_id__in=followed_users)
            .exclude(book_id__in=excluded_book_ids)
            .select_related('user', 'book')
        )
        for entry in followed_entries:
            b_id = entry.book_id
            pts = 1.0
            if entry.rating and entry.rating >= 4:
                pts += 1.5
            elif entry.status == ReadingStatus.READ:
                pts += 0.8
            social_book_scores[b_id] += pts
            username = entry.user.username
            if username not in social_book_friends[b_id]:
                social_book_friends[b_id].append(username)

        # Normalizar puntuación social
        max_social = max(social_book_scores.values()) if social_book_scores else 1.0
        for bid in social_book_scores:
            social_book_scores[bid] /= max_social

    # 4. Obtener candidatos viables del catálogo general
    candidate_qs = (
        Book.objects.exclude(id__in=excluded_book_ids)
        .select_related('author')
        .prefetch_related('categories')
    )

    # Puntuación de cada candidato
    scored_candidates: list[dict] = []

    # Mapas auxiliares para nombres amigables
    categories_map = {c.id: c.name for c in Category.objects.all()}

    for book in candidate_qs[:200]:
        score_genre = 0.0
        score_author = 0.0
        score_social = social_book_scores.get(book.id, 0.0)
        score_semantic = 0.0
        score_discovery = 0.0

        # Puntuación por categoría
        book_cat_ids = [c.id for c in book.categories.all()]
        for cid in book_cat_ids:
            if cid in cat_affinity:
                score_genre = max(score_genre, cat_affinity[cid])

        # Puntuación por autor
        if book.author_id and book.author_id in auth_affinity:
            score_author = auth_affinity[book.author_id]

        # Puntuación semántica / coincidencia de palabras clave
        if fav_keywords:
            text = f"{book.title} {book.description or ''}".lower()
            matches = sum(1 for kw in fav_keywords if kw in text)
            score_semantic = min(1.0, matches / 3.0)

        # Puntuación por descubrimiento / calidad media comunitaria
        if book.average_rating and book.average_rating >= 4.0:
            score_discovery = (book.average_rating - 3.5) / 1.5

        # Ponderación según estrategia
        if strategy == 'rules':
            total = (score_genre * 0.6) + (score_author * 0.4)
        elif strategy == 'social':
            total = (score_social * 0.7) + (score_genre * 0.3)
        elif strategy == 'semantic':
            total = (score_semantic * 0.7) + (score_genre * 0.3)
        else:  # hybrid
            total = (
                (score_genre * w['genre_preferences'])
                + (score_author * w['author_affinity'])
                + (score_social * w['social_behavior'])
                + (score_semantic * w['semantic_similarity'])
                + (score_discovery * w['discovery'])
            )

        # Determinación del motivo explicativo principal (Explainability)
        reason = "Aclamado por la comunidad de lectores"
        if score_author > 0.4 and book.author:
            reason = f"Porque te gustó el estilo de {book.author.name}"
        elif score_social > 0.3 and book.id in social_book_friends:
            friends = social_book_friends[book.id]
            if len(friends) == 1:
                reason = f"Leído y valorado por tu amigo @{friends[0]}"
            else:
                reason = f"Popular entre las personas que sigues (@{friends[0]} y otros)"
        elif score_genre > 0.3 and book_cat_ids:
            first_cat_name = categories_map.get(book_cat_ids[0], 'tu género favorito')
            reason = f"Basado en tu interés por {first_cat_name}"
        elif score_semantic > 0.4:
            reason = "Afinidad temática con tus lecturas recientes"
        elif score_discovery > 0.5:
            reason = "Joya destacada con alta valoración en la comunidad"

        if total > 0.05 or not cat_affinity:
            scored_candidates.append({
                'book': book,
                'score': total,
                'reason': reason,
            })

    # Ordenar candidatos por mayor puntuación
    scored_candidates.sort(key=lambda x: x['score'], reverse=True)

    # 5. Cold-Start Fallback: si el usuario no tiene historial o no hay suficientes sugerencias
    if len(scored_candidates) < limit:
        existing_ids = {c['book'].id for c in scored_candidates} | excluded_book_ids
        fallback_books = (
            Book.objects.exclude(id__in=existing_ids)
            .annotate(num_readers=Count('user_entries'))
            .order_by('-average_rating', '-num_readers')[:limit - len(scored_candidates)]
        )
        for fb in fallback_books:
            scored_candidates.append({
                'book': fb,
                'score': 0.1,
                'reason': "Lectura popular recomendada para empezar tu viaje",
            })

    results = []
    for item in scored_candidates[:limit]:
        b = item['book']
        results.append({
            'id': b.id,
            'title': b.title,
            'author_name': b.author.name if b.author else 'Autor desconocido',
            'cover': build_media_url(b.cover.name if b.cover else None, request=request),
            'average_rating': b.average_rating,
            'score': round(float(item['score']), 2),
            'reason': item['reason'],
        })

    # Guardar en caché
    cache.set(cache_key, results, timeout=TTL_RECOMMENDATIONS)
    return results


def get_book_recommendations(
    book_id: int | str,
    limit: int = 6,
    user=None,
    request=None,
) -> list[dict]:
    """
    Genera recomendaciones contextuales para la ficha de un libro específico (Item-to-Item).
    Aplica filtrado colaborativo ("quienes leyeron este libro también leyeron...")
    combinado con afinidad por autor y categorías.
    """
    cache_key = book_recommendations_key(book_id)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    try:
        source_book = (
            Book.objects.select_related('author')
            .prefetch_related('categories')
            .get(pk=book_id)
        )
    except Book.DoesNotExist:
        return []

    excluded_ids = {source_book.id}
    if user and user.is_authenticated:
        user_books = UserBook.objects.filter(user=user).values_list('book_id', flat=True)
        excluded_ids.update(user_books)

    # 1. Filtrado colaborativo: lectores que leyeron este libro
    co_readers = UserBook.objects.filter(book_id=source_book.id).values_list('user_id', flat=True)
    co_read_books = (
        UserBook.objects.filter(user_id__in=co_readers)
        .exclude(book_id__in=excluded_ids)
        .values('book_id')
        .annotate(co_count=Count('id'))
        .order_by('-co_count')[:limit * 2]
    )
    co_read_map = {item['book_id']: item['co_count'] for item in co_read_books}

    # 2. Candidatos por autor y categorías
    source_cat_ids = list(source_book.categories.values_list('id', flat=True))
    candidates = (
        Book.objects.exclude(id__in=excluded_ids)
        .filter(
            Q(author_id=source_book.author_id)
            | Q(categories__in=source_cat_ids)
            | Q(id__in=list(co_read_map.keys()))
        )
        .distinct()
        .select_related('author')
        .prefetch_related('categories')[:50]
    )

    scored_items = []
    for candidate in candidates:
        score = 0.0
        reason = "Libro similar de interés"

        # Co-lecturas colaborativas (mayor peso)
        if candidate.id in co_read_map:
            score += 3.0 * co_read_map[candidate.id]
            reason = "Lectores de este libro también disfrutaron este título"

        # Mismo autor
        if source_book.author_id and candidate.author_id == source_book.author_id:
            score += 2.5
            if score < 4.0:
                reason = f"Del mismo autor ({source_book.author.name})"

        # Categorías compartidas
        cand_cats = set(candidate.categories.values_list('id', flat=True))
        shared_cats = cand_cats.intersection(source_cat_ids)
        if shared_cats:
            score += 1.5 * len(shared_cats)
            if score < 3.0:
                reason = "Comparte temática y género literario similar"

        if candidate.average_rating:
            score += candidate.average_rating * 0.2

        scored_items.append({
            'book': candidate,
            'score': score,
            'reason': reason,
        })

    scored_items.sort(key=lambda x: x['score'], reverse=True)

    results = []
    for item in scored_items[:limit]:
        b = item['book']
        results.append({
            'id': b.id,
            'title': b.title,
            'author_name': b.author.name if b.author else 'Autor desconocido',
            'cover': build_media_url(b.cover.name if b.cover else None, request=request),
            'average_rating': b.average_rating,
            'score': round(float(item['score']), 2),
            'reason': item['reason'],
        })

    cache.set(cache_key, results, timeout=TTL_RECOMMENDATIONS)
    return results

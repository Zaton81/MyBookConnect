"""
Motor de Recomendaciones v1 para MyBookConnect.

Fase 49 del Roadmap: Algoritmo inicial transparente sin Machine Learning complejo,
estructurado como una suma ponderada de 5 variables canónicas:
1. Género (afinidad de categorías extraída de lecturas y valoraciones)
2. Autor (afinidad de autores leídos y positivamente valorados)
3. Rating (calidad media del libro candidato y umbral del lector)
4. Historial (experiencia acumulada, libros leídos y en curso)
5. Wishlist (intención explícita basada en libros en 'WANT_TO_READ' y listas de deseos)

Fórmula:
    score = (w_genre * S_genre) + (w_author * S_author) +
            (w_rating * S_rating) + (w_history * S_history) +
            (w_wishlist * S_wishlist)

Versión del algoritmo: 'v1'
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from django.core.cache import cache
from django.db.models import Count, QuerySet

from books.cache_utils import TTL_RECOMMENDATIONS, user_recommendations_key
from books.media_utils import build_media_url
from books.models import Book, Category, ReadingList, ReadingListItem, ReadingStatus, UserBook

logger = logging.getLogger(__name__)

ALGORITHM_VERSION = "v1"

# Pesos por defecto para el cálculo de suma ponderada v1 (suma = 1.0)
DEFAULT_V1_WEIGHTS = {
    'genre': 0.30,
    'author': 0.25,
    'rating': 0.15,
    'history': 0.15,
    'wishlist': 0.15,
}


@dataclass
class ScoreBreakdownV1:
    genre: float = 0.0
    author: float = 0.0
    rating: float = 0.0
    history: float = 0.0
    wishlist: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return {
            'genre': round(self.genre, 4),
            'author': round(self.author, 4),
            'rating': round(self.rating, 4),
            'history': round(self.history, 4),
            'wishlist': round(self.wishlist, 4),
        }


@dataclass
class RecommendationV1Item:
    book: Book
    score: float
    reason: str
    algorithm_version: str = ALGORITHM_VERSION
    breakdown: ScoreBreakdownV1 = field(default_factory=ScoreBreakdownV1)

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
            'scores': self.breakdown.to_dict(),  # Alias para compatibilidad
            'reason': self.reason,
        }


@dataclass
class UserProfileV1:
    category_affinity: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    author_affinity: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    wishlist_categories: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    wishlist_authors: dict[int, float] = field(default_factory=lambda: defaultdict(float))
    read_count: int = 0
    reading_count: int = 0
    total_rated: int = 0
    avg_given_rating: float = 0.0
    excluded_book_ids: set[int] = field(default_factory=set)


class RecommendationEngineV1:
    """
    Motor determinista de recomendaciones v1 basado en suma ponderada
    de 5 variables canónicas: género, autor, rating, historial y wishlist.
    """

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = dict(DEFAULT_V1_WEIGHTS)
        if weights:
            # Normalizar y sobreescribir pesos provistos
            valid_keys = set(DEFAULT_V1_WEIGHTS.keys())
            for k, v in weights.items():
                if k in valid_keys and isinstance(v, (int, float)) and v >= 0:
                    self.weights[k] = float(v)

            total = sum(self.weights.values())
            if total > 0:
                for k in self.weights:
                    self.weights[k] /= total

    def compute_user_profile(self, user) -> UserProfileV1:
        """
        Extrae y normaliza las 5 dimensiones del perfil lector del usuario:
        historial de lectura, afinidad por géneros, afinidad por autores,
        comportamiento de valoración y libros guardados en lista de deseos.
        """
        profile = UserProfileV1()
        if not user or not user.is_authenticated:
            return profile

        user_entries = (
            UserBook.objects.filter(user=user)
            .select_related('book', 'book__author')
            .prefetch_related('book__categories')
        )

        ratings_sum = 0.0

        for entry in user_entries:
            b = entry.book
            profile.excluded_book_ids.add(b.id)

            # 1. Dimensión de Wishlist (WANT_TO_READ)
            if entry.status == ReadingStatus.WANT_TO_READ:
                for cat in b.categories.all():
                    profile.wishlist_categories[cat.id] += 1.0
                if b.author_id:
                    profile.wishlist_authors[b.author_id] += 1.0

            # 2. Dimensión de Historial (READ y READING)
            if entry.status == ReadingStatus.READ:
                profile.read_count += 1
            elif entry.status == ReadingStatus.READING:
                profile.reading_count += 1

            # 3. Ponderación para Afinidad de Género y Autor
            weight = 0.5  # Peso base por interacción
            if entry.rating:
                profile.total_rated += 1
                ratings_sum += float(entry.rating)
                # Escala [0.2, 1.2] según la puntuación otorgada (1-5 estrellas)
                weight = 0.2 + (float(entry.rating) / 5.0)
            elif entry.status == ReadingStatus.READ:
                weight = 0.9
            elif entry.status == ReadingStatus.READING:
                weight = 0.7
            elif entry.status == ReadingStatus.WANT_TO_READ:
                weight = 0.6

            for cat in b.categories.all():
                profile.category_affinity[cat.id] += weight

            if b.author_id:
                profile.author_affinity[b.author_id] += weight

        # Incluir también listas personalizadas marcadas como 'wishlist' o 'deseos'
        try:
            wishlist_lists = ReadingList.objects.filter(
                user=user,
                slug__icontains='deseo',
            ).values_list('id', flat=True)
            if wishlist_lists:
                custom_items = (
                    ReadingListItem.objects.filter(reading_list_id__in=wishlist_lists)
                    .select_related('book', 'book__author')
                    .prefetch_related('book__categories')
                )
                for item in custom_items:
                    profile.excluded_book_ids.add(item.book_id)
                    for cat in item.book.categories.all():
                        profile.wishlist_categories[cat.id] += 1.2
                    if item.book.author_id:
                        profile.wishlist_authors[item.book.author_id] += 1.2
        except Exception as exc:
            logger.debug("Error procesando listas personalizadas para wishlist: %s", exc)

        if profile.total_rated > 0:
            profile.avg_given_rating = ratings_sum / profile.total_rated

        # Normalización a escala [0, 1]
        max_cat = max(profile.category_affinity.values()) if profile.category_affinity else 1.0
        for cid in profile.category_affinity:
            profile.category_affinity[cid] /= max_cat

        max_auth = max(profile.author_affinity.values()) if profile.author_affinity else 1.0
        for aid in profile.author_affinity:
            profile.author_affinity[aid] /= max_auth

        max_wl_cat = max(profile.wishlist_categories.values()) if profile.wishlist_categories else 1.0
        for cid in profile.wishlist_categories:
            profile.wishlist_categories[cid] /= max_wl_cat

        max_wl_auth = max(profile.wishlist_authors.values()) if profile.wishlist_authors else 1.0
        for aid in profile.wishlist_authors:
            profile.wishlist_authors[aid] /= max_wl_auth

        return profile

    def score_candidate(self, book: Book, profile: UserProfileV1) -> RecommendationV1Item:
        """
        Calcula el score de un libro candidato evaluando las 5 variables canónicas:
        1. S_genre: Coincidencia con categorías afines del usuario
        2. S_author: Afinidad hacia el autor
        3. S_rating: Calidad comunitaria y atractivo de valoración
        4. S_history: Nivel de experiencia del lector y coherencia histórica
        5. S_wishlist: Relevancia respecto a libros en lista de deseos
        """
        w = self.weights
        book_cat_ids = [c.id for c in book.categories.all()]

        # 1. Variable GÉNERO (S_genre)
        s_genre = 0.0
        matched_cat_name = None
        for cid in book_cat_ids:
            if cid in profile.category_affinity:
                val = profile.category_affinity[cid]
                if val > s_genre:
                    s_genre = val

        # 2. Variable AUTOR (S_author)
        s_author = 0.0
        if book.author_id and book.author_id in profile.author_affinity:
            s_author = profile.author_affinity[book.author_id]

        # 3. Variable RATING (S_rating)
        # Normaliza la calificación del libro (base 3.0 -> 5.0 a rango 0.0 -> 1.0)
        s_rating = 0.0
        avg_rat = book.average_rating or 0.0
        if avg_rat > 0:
            s_rating = min(1.0, max(0.0, (avg_rat - 3.0) / 2.0))

        # 4. Variable HISTORIAL (S_history)
        # Factor que premia a libros adecuados para el volumen y ritmo del lector
        # Usuarios avanzados (más lecturas) aprovechan catálogos con mayor diversidad
        s_history = 0.0
        total_history = profile.read_count + profile.reading_count
        if total_history > 0:
            # Señal de madurez lectora normalizada (hasta 20 libros)
            user_maturity = min(1.0, total_history / 15.0)
            # Refuerzo si el libro encaja con al menos autor o género previo
            affinity_factor = max(s_genre, s_author)
            s_history = (user_maturity * 0.4) + (affinity_factor * 0.6)

        # 5. Variable WISHLIST (S_wishlist)
        # Proximidad con temas o autores que el usuario tiene pendientes en WANT_TO_READ
        s_wishlist = 0.0
        if profile.wishlist_authors and book.author_id in profile.wishlist_authors:
            s_wishlist = max(s_wishlist, profile.wishlist_authors[book.author_id])

        for cid in book_cat_ids:
            if cid in profile.wishlist_categories:
                s_wishlist = max(s_wishlist, profile.wishlist_categories[cid] * 0.8)

        # SUMA PONDERADA CANÓNICA V1
        total_score = (
            (w['genre'] * s_genre)
            + (w['author'] * s_author)
            + (w['rating'] * s_rating)
            + (w['history'] * s_history)
            + (w['wishlist'] * s_wishlist)
        )

        breakdown = ScoreBreakdownV1(
            genre=s_genre,
            author=s_author,
            rating=s_rating,
            history=s_history,
            wishlist=s_wishlist,
        )

        # EXPLICABILIDAD TRANSPARENTE (REASON)
        # Basada en la variable con mayor aporte ponderado
        weighted_contributions = {
            'genre': w['genre'] * s_genre,
            'author': w['author'] * s_author,
            'wishlist': w['wishlist'] * s_wishlist,
            'rating': w['rating'] * s_rating,
            'history': w['history'] * s_history,
        }
        dominant_factor = max(weighted_contributions, key=weighted_contributions.get)

        if dominant_factor == 'author' and s_author > 0.3 and book.author:
            reason = f"Porque te gusta la obra de {book.author.name}"
        elif dominant_factor == 'wishlist' and s_wishlist > 0.3:
            reason = "Alineado con los libros pendientes en tu lista de deseos"
        elif dominant_factor == 'genre' and s_genre > 0.2:
            first_cat = book.categories.first()
            cat_label = first_cat.name if first_cat else "tus géneros preferidos"
            reason = f"Basado en tu interés por {cat_label}"
        elif dominant_factor == 'rating' and s_rating > 0.5:
            reason = f"Obra destacada y aclamada por la comunidad ({avg_rat:.1f} ★)"
        elif dominant_factor == 'history' and s_history > 0.3:
            reason = "Recomendado por encajar con tu trayectoria lectora"
        else:
            reason = "Recomendado por la comunidad de lectores de MyBookConnect"

        return RecommendationV1Item(
            book=book,
            score=min(1.0, max(0.0, total_score)),
            reason=reason,
            algorithm_version=ALGORITHM_VERSION,
            breakdown=breakdown,
        )

    def recommend(
        self,
        user,
        limit: int = 10,
        request=None,
    ) -> list[dict[str, Any]]:
        """
        Genera el listado ordenado de recomendaciones personalizadas v1 para un usuario.
        Aplica exclusión estricta de biblioteca propia, ranking por suma ponderada,
        resolución de arranque en frío (Cold Start) y cacheo reactivo.
        """
        if not user or not user.is_authenticated:
            return []

        cache_key = user_recommendations_key(user.id, strategy='v1')
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        profile = self.compute_user_profile(user)

        # Candidatos viables: libros que el usuario no tiene en su biblioteca
        candidate_qs: QuerySet[Book] = (
            Book.objects.exclude(id__in=profile.excluded_book_ids)
            .select_related('author')
            .prefetch_related('categories')
        )

        scored_items: list[RecommendationV1Item] = []

        # Evaluar candidatos principales
        for book in candidate_qs[:250]:
            item = self.score_candidate(book, profile)
            if item.score > 0.05 or not profile.category_affinity:
                scored_items.append(item)

        # Ordenar descendentemente por score ponderado y rating
        scored_items.sort(
            key=lambda x: (x.score, x.book.average_rating or 0.0),
            reverse=True,
        )

        # ARRANQUE EN FRÍO (Cold-Start Fallback):
        # Si el usuario es nuevo o tiene pocos candidatos, complementar con los más populares
        if len(scored_items) < limit:
            existing_ids = {it.book.id for it in scored_items} | profile.excluded_book_ids
            needed = limit - len(scored_items)
            fallback_books = (
                Book.objects.exclude(id__in=existing_ids)
                .annotate(num_readers=Count('user_entries'))
                .order_by('-average_rating', '-num_readers')[:needed]
            )
            for fb in fallback_books:
                fb_item = RecommendationV1Item(
                    book=fb,
                    score=0.10,
                    reason="Lectura popular recomendada para empezar tu viaje en MyBookConnect",
                    algorithm_version=ALGORITHM_VERSION,
                    breakdown=ScoreBreakdownV1(
                        rating=min(1.0, (fb.average_rating or 3.5) / 5.0),
                    ),
                )
                scored_items.append(fb_item)

        results = [item.to_dict(request=request) for item in scored_items[:limit]]

        # Guardar en caché con el TTL estándar
        cache.set(cache_key, results, timeout=TTL_RECOMMENDATIONS)
        return results


def recommend_books_v1(user, limit: int = 10, weights: dict[str, float] | None = None, request=None) -> list[dict[str, Any]]:
    """Función de conveniencia para invocar el motor de recomendaciones v1."""
    engine = RecommendationEngineV1(weights=weights)
    return engine.recommend(user=user, limit=limit, request=request)

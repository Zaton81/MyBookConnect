import logging
from dataclasses import dataclass

from django.contrib.postgres.search import (
    SearchQuery,
    SearchRank,
    SearchVector,
    TrigramSimilarity,
    TrigramWordSimilarity,
)
from django.core.cache import cache
from django.db import connection
from django.db.models import Case, FloatField, IntegerField, Q, QuerySet, When
from django.db.models.functions import Coalesce, Greatest

from ai.embeddings import cosine_similarity, get_embedding_for_text
from ai.services import semantic_search_books
from books.models import Book, BookEmbedding, EmbeddingStatus
from books.services.import_service import import_multiple_by_title, import_single_by_query

logger = logging.getLogger(__name__)


@dataclass
class SearchResultItem:
    """Representa una coincidencia individual con desglose de relevancia multicanal."""
    book: Book
    unified_score: float
    match_type: str  # 'exact', 'fuzzy', 'semantic', 'hybrid'
    text_score: float = 0.0
    fuzzy_score: float = 0.0
    semantic_score: float = 0.0


class UnifiedSearchEngine:
    """
    Motor de Búsqueda Unificado para MyBookConnect.
    Integra en una sola canalización:
    1. Búsqueda Textual (PostgreSQL FTS con SearchVector y SearchRank).
    2. Búsqueda Difusa (TrigramSimilarity y TrigramWordSimilarity tolerante a erratas).
    3. Búsqueda Semántica (Embeddings vectoriales + similitud coseno + expansión temática).
    4. Fusión Ponderada y Re-ranking por reputación comunitaria.
    """

    DEFAULT_WEIGHTS = {
        'hybrid': {'text': 0.45, 'fuzzy': 0.35, 'semantic': 0.20},
        'text': {'text': 1.0, 'fuzzy': 0.0, 'semantic': 0.0},
        'fuzzy': {'text': 0.0, 'fuzzy': 1.0, 'semantic': 0.0},
        'semantic': {'text': 0.0, 'fuzzy': 0.0, 'semantic': 1.0},
    }

    def __init__(self, mode: str = 'hybrid'):
        self.mode = mode.lower().strip() if mode else 'hybrid'
        if self.mode not in self.DEFAULT_WEIGHTS:
            self.mode = 'hybrid'
        self.weights = self.DEFAULT_WEIGHTS[self.mode]

    def search(
        self,
        query: str,
        category: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        limit: int = 20,
        offset: int = 0,
        auto_import: bool = True,
    ) -> tuple[list[SearchResultItem], int]:
        """
        Ejecuta la búsqueda unificada devolviendo los resultados ordenados por relevancia.
        """
        clean_q = query.strip() if query else ''
        if not clean_q:
            base_qs = self._build_base_queryset(category, author, min_rating)
            total = base_qs.count()
            items = [
                SearchResultItem(
                    book=b,
                    unified_score=0.0,
                    match_type='catalog',
                )
                for b in base_qs[offset : offset + limit]
            ]
            return items, total

        # Ejecutar búsqueda en base de datos local
        results = self._execute_unified_pipeline(clean_q, category, author, min_rating)

        # Determinar si existe al menos una coincidencia fuerte
        has_strong_match = False
        if results:
            top_item = results[0]
            title_lower = (top_item.book.title or '').lower()
            q_lower = clean_q.lower()
            if top_item.unified_score >= 0.35 or q_lower in title_lower or title_lower in q_lower:
                has_strong_match = True

        # Fallback de importación externa automática si no hay coincidencias firmes
        if auto_import and (not has_strong_match or len(results) == 0) and len(clean_q) >= 3:
            try:
                isbn_clean = clean_q.replace('-', '').replace(' ', '')
                if len(isbn_clean) in (10, 13) and (
                    isbn_clean[:-1].isdigit() and (isbn_clean[-1].isdigit() or isbn_clean[-1].upper() == 'X')
                ):
                    import_single_by_query(query_isbn=isbn_clean)
                else:
                    import_multiple_by_title(clean_q, offset=0)

                # Reevaluar la búsqueda tras la importación
                results = self._execute_unified_pipeline(clean_q, category, author, min_rating)
            except Exception as exc:
                logger.warning("Error en auto-importación externa para '%s': %s", clean_q, exc)

        # Encolar descarga de portadas en segundo plano para los libros sin portada
        self._enqueue_missing_covers(results[:10])

        total = len(results)
        paginated_items = results[offset : offset + limit]
        return paginated_items, total

    def search_queryset(
        self,
        query: str,
        category: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
        limit: int = 100,
        auto_import: bool = True,
    ) -> QuerySet:
        """
        Ejecuta la búsqueda y devuelve un QuerySet de Django preservando
        el orden jerárquico del ranking unificado multicanal.
        """
        items, _ = self.search(
            query=query,
            category=category,
            author=author,
            min_rating=min_rating,
            limit=limit,
            offset=0,
            auto_import=auto_import,
        )
        if not items:
            return Book.objects.none()

        ordered_ids = [item.book.id for item in items]
        preserved_order = Case(
            *[When(id=pk, then=pos) for pos, pk in enumerate(ordered_ids)],
            output_field=IntegerField(),
        )
        return (
            Book.objects.filter(id__in=ordered_ids)
            .select_related('author')
            .prefetch_related('categories')
            .order_by(preserved_order)
        )


    def _build_base_queryset(
        self,
        category: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
    ) -> QuerySet:
        qs = Book.objects.select_related('author').prefetch_related('categories')
        if category:
            cat_str = str(category).strip()
            if cat_str.isdigit():
                qs = qs.filter(Q(categories__name__iexact=cat_str) | Q(categories__id=int(cat_str)))
            else:
                qs = qs.filter(
                    Q(categories__name__iexact=cat_str)
                    | Q(categories__slug__iexact=cat_str)
                    | Q(categories__name__icontains=cat_str)
                )
        if author:
            auth_str = str(author).strip()
            if auth_str.isdigit():
                qs = qs.filter(Q(author__name__icontains=auth_str) | Q(author__id=int(auth_str)))
            else:
                if connection.vendor == 'postgresql':
                    qs = qs.filter(
                        Q(author__name__icontains=auth_str)
                        | Q(author__name__trigram_similar=auth_str)
                        | Q(author__name__trigram_word_similar=auth_str)
                    )
                else:
                    qs = qs.filter(Q(author__name__icontains=auth_str))
        if min_rating is not None:
            try:
                qs = qs.filter(average_rating__gte=float(min_rating))
            except (ValueError, TypeError):
                pass
        return qs

    def _execute_unified_pipeline(
        self,
        query_str: str,
        category: str | None = None,
        author: str | None = None,
        min_rating: float | None = None,
    ) -> list[SearchResultItem]:
        base_qs = self._build_base_queryset(category, author, min_rating)

        text_scores: dict[int, float] = {}
        fuzzy_scores: dict[int, float] = {}
        semantic_scores: dict[int, float] = {}
        candidates_map: dict[int, Book] = {}

        # 1. Canal Textual (FTS PostgreSQL)
        if self.weights['text'] > 0.0:
            text_matches = self._execute_textual_search(query_str, base_qs)
            for book, score in text_matches:
                candidates_map[book.id] = book
                text_scores[book.id] = score

        # 2. Canal Fuzzy (pg_trgm)
        if self.weights['fuzzy'] > 0.0:
            fuzzy_matches = self._execute_fuzzy_search(query_str, base_qs)
            for book, score in fuzzy_matches:
                candidates_map[book.id] = book
                fuzzy_scores[book.id] = score

        # 3. Canal Semántico (Vector Embeddings / Thematic)
        if self.weights['semantic'] > 0.0:
            semantic_matches = self._execute_semantic_search(query_str, base_qs)
            for book, score in semantic_matches:
                candidates_map[book.id] = book
                semantic_scores[book.id] = score

        # Fusión y ranking final
        return self._blend_and_rank(
            candidates_map,
            text_scores,
            fuzzy_scores,
            semantic_scores,
            query_str=query_str,
        )

    def _execute_textual_search(self, query_str: str, base_qs: QuerySet) -> list[tuple[Book, float]]:
        is_postgres = connection.vendor == 'postgresql'
        if is_postgres:
            try:
                vector = (
                    SearchVector('title', weight='A', config='spanish')
                    + SearchVector('isbn', weight='A', config='spanish')
                    + SearchVector('author__name', weight='B', config='spanish')
                    + SearchVector('categories__name', weight='B', config='spanish')
                    + SearchVector('description', weight='C', config='spanish')
                )
                search_query = SearchQuery(query_str, config='spanish')
                rank = SearchRank(vector, search_query)

                matched = (
                    base_qs.annotate(rank=rank)
                    .filter(
                        Q(rank__gte=0.01)
                        | Q(title__icontains=query_str)
                        | Q(isbn__icontains=query_str)
                        | Q(author__name__icontains=query_str)
                        | Q(description__icontains=query_str)
                    )
                    .distinct()
                )

                results = []
                for b in matched[:50]:
                    raw_rank = getattr(b, 'rank', 0.0) or 0.0
                    # Normalizar rank FTS a escala [0, 1]
                    normalized = min(1.0, float(raw_rank) * 1.5)
                    # Boost si hay coincidencia exacta de prefijo o título
                    if query_str.lower() in (b.title or '').lower():
                        normalized = max(normalized, 0.85)
                    results.append((b, normalized))
                return results
            except Exception as exc:
                logger.warning("FTS search fallback to icontains: %s", exc)

        # Fallback SQL estándar
        matched = (
            base_qs.filter(
                Q(title__icontains=query_str)
                | Q(isbn__icontains=query_str)
                | Q(author__name__icontains=query_str)
                | Q(categories__name__icontains=query_str)
                | Q(description__icontains=query_str)
            )
            .distinct()[:50]
        )
        results = []
        for b in matched:
            title_lower = (b.title or '').lower()
            q_lower = query_str.lower()
            score = 0.9 if q_lower == title_lower else (0.7 if q_lower in title_lower else 0.4)
            results.append((b, score))
        return results

    def _execute_fuzzy_search(self, query_str: str, base_qs: QuerySet) -> list[tuple[Book, float]]:
        is_postgres = connection.vendor == 'postgresql'
        if not is_postgres:
            return []

        try:
            # Similitud trigramática en título, autor y sinopsis
            title_sim = TrigramSimilarity('title', query_str)
            title_word_sim = TrigramWordSimilarity(query_str, 'title')
            author_sim = TrigramSimilarity('author__name', query_str)
            author_word_sim = TrigramWordSimilarity(query_str, 'author__name')
            desc_sim = TrigramSimilarity('description', query_str)

            max_title = Greatest(title_sim, title_word_sim, output_field=FloatField())
            max_author = Greatest(author_sim, author_word_sim, output_field=FloatField())

            # Fórmula de ponderación fuzzy
            fuzzy_expr = (
                Coalesce(max_title, 0.0) * 3.0
                + Coalesce(max_author, 0.0) * 2.0
                + Coalesce(desc_sim, 0.0) * 0.5
            ) / 5.5

            matched = (
                base_qs.annotate(fuzzy_score=fuzzy_expr)
                .filter(
                    Q(title__trigram_similar=query_str)
                    | Q(title__trigram_word_similar=query_str)
                    | Q(author__name__trigram_similar=query_str)
                    | Q(author__name__trigram_word_similar=query_str)
                    | Q(fuzzy_score__gte=0.15)
                )
                .distinct()
                .order_by('-fuzzy_score')[:50]
            )

            results = []
            for b in matched:
                score = min(1.0, float(getattr(b, 'fuzzy_score', 0.0) or 0.0))
                results.append((b, score))
            return results
        except Exception as exc:
            logger.warning("Fuzzy trigram search error: %s", exc)
            return []

    def _execute_semantic_search(self, query_str: str, base_qs: QuerySet) -> list[tuple[Book, float]]:
        results: list[tuple[Book, float]] = []
        allowed_ids = set(base_qs.values_list('id', flat=True))

        # 1. Intentar cálculo vectorial directo contra BookEmbedding persistido
        query_emb = None
        try:
            query_emb = get_embedding_for_text(query_str)
        except Exception as exc:
            logger.debug("No se pudo obtener embedding para '%s': %s", query_str, exc)

        if query_emb and isinstance(query_emb, list) and len(query_emb) > 0:
            embeddings_qs = (
                BookEmbedding.objects.filter(
                    embedding_status=EmbeddingStatus.COMPLETED,
                    book_id__in=allowed_ids,
                )
                .select_related('book')
            )
            for emb_rec in embeddings_qs:
                if emb_rec.vector and isinstance(emb_rec.vector, list) and len(emb_rec.vector) > 0:
                    sim = cosine_similarity(query_emb, emb_rec.vector)
                    if sim > 0.15:
                        results.append((emb_rec.book, float(sim)))

        # 2. Si no hay resultados vectoriales directos, usar expansión conceptual temática
        if not results:
            semantic_candidates = semantic_search_books(query_str, limit=30)
            for rank_idx, b in enumerate(semantic_candidates):
                if b.id in allowed_ids:
                    score = max(0.2, 0.85 - (rank_idx * 0.03))
                    results.append((b, score))

        return results

    def _blend_and_rank(
        self,
        candidates_map: dict[int, Book],
        text_scores: dict[int, float],
        fuzzy_scores: dict[int, float],
        semantic_scores: dict[int, float],
        query_str: str = '',
    ) -> list[SearchResultItem]:
        w_text = self.weights['text']
        w_fuzzy = self.weights['fuzzy']
        w_semantic = self.weights['semantic']
        q_norm = query_str.lower().strip()

        ranked_items: list[SearchResultItem] = []

        for book_id, book in candidates_map.items():
            s_text = text_scores.get(book_id, 0.0)
            s_fuzzy = fuzzy_scores.get(book_id, 0.0)
            s_semantic = semantic_scores.get(book_id, 0.0)

            # Cálculo ponderado multicanal
            unified = (w_text * s_text) + (w_fuzzy * s_fuzzy) + (w_semantic * s_semantic)

            # Jerarquía de ranking determinista (Sección 11.2):
            # 1. Exact match (+1.0)
            # 2. Prefix match (+0.5)
            # 3. Factor de calidad moderado (rating + popularidad <= 0.12)
            title_norm = (book.title or '').lower().strip()
            boost = 0.0
            is_exact = False
            is_prefix = False

            if q_norm and title_norm:
                if q_norm == title_norm:
                    boost += 1.0
                    is_exact = True
                elif title_norm.startswith(q_norm):
                    boost += 0.5
                    is_prefix = True

            avg_rating = book.average_rating or 0.0
            rating_boost = (avg_rating / 5.0) * 0.08 if avg_rating > 0 else 0.0
            popularity_boost = min(0.04, float(getattr(book, 'reviews_count', 0) or 0) * 0.004)

            final_score = round(unified + boost + rating_boost + popularity_boost, 4)

            # Clasificación de tipo de coincidencia
            if is_exact:
                match_type = 'exact'
            elif (s_text >= 0.4 and (s_fuzzy >= 0.3 or s_semantic >= 0.3)) or (s_fuzzy >= 0.3 and s_semantic >= 0.3):
                match_type = 'hybrid'
            elif is_prefix or (s_text >= 0.7 and s_fuzzy < 0.5):
                match_type = 'exact'
            elif s_fuzzy >= 0.35 and s_text < 0.4:
                match_type = 'fuzzy'
            elif s_semantic >= 0.35 and s_text < 0.3 and s_fuzzy < 0.3:
                match_type = 'semantic'
            else:
                match_type = 'hybrid'

            ranked_items.append(
                SearchResultItem(
                    book=book,
                    unified_score=final_score,
                    match_type=match_type,
                    text_score=round(s_text, 4),
                    fuzzy_score=round(s_fuzzy, 4),
                    semantic_score=round(s_semantic, 4),
                )
            )

        # Paginación determinista (Sección 11.3): orden descendente por unified_score y desempate estable por -book.id
        ranked_items.sort(
            key=lambda item: (item.unified_score, -(item.book.id)),
            reverse=True,
        )
        return ranked_items

    def _enqueue_missing_covers(self, items: list[SearchResultItem]):
        for item in items:
            book = item.book
            if not book.cover:
                bg_key = f"bg_cover_search_{book.id}"
                if not cache.get(bg_key):
                    try:
                        from books.tasks import download_cover_task
                        download_cover_task.delay(book.id)
                        cache.set(bg_key, True, 600)
                    except Exception as exc:
                        logger.debug("Error programando descarga de portada: %s", exc)


def unified_book_search(
    query: str,
    mode: str = 'hybrid',
    category: str | None = None,
    author: str | None = None,
    min_rating: float | None = None,
    limit: int = 20,
    offset: int = 0,
    auto_import: bool = True,
) -> tuple[list[SearchResultItem], int]:
    """Función de conveniencia para ejecutar búsquedas unificadas."""
    engine = UnifiedSearchEngine(mode=mode)
    return engine.search(
        query=query,
        category=category,
        author=author,
        min_rating=min_rating,
        limit=limit,
        offset=offset,
        auto_import=auto_import,
    )

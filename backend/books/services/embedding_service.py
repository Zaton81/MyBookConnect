"""
Servicio para ciclo de vida, vectorización, normalización y re-embedding de libros (Fase 25 - Embeddings y pgvector).

Implementa la canalización de arquitectura según el Roadmap:
Book -> Content Normalization -> Embedding Job -> Persistencia -> ANN Search -> Hybrid Ranking.
Gobierna estrictamente el versionado para nunca mezclar embeddings de modelos incompatibles.
"""

import hashlib
import logging
import re
import unicodedata
from typing import Any

from django.db.models import Count
from django.utils import timezone

from ai.config import get_ai_settings
from ai.embeddings import cosine_similarity, get_embedding_for_text
from books.models import Book, BookEmbedding, EmbeddingStatus

logger = logging.getLogger(__name__)


def normalize_book_content_for_embedding(book: Book) -> tuple[str, str]:
    """
    Normaliza el contenido textual canónico de una obra literaria para su vectorización (Fase 25).
    Limpia etiquetas HTML, normaliza caracteres unicode, compacta espacios en blanco y
    genera una huella criptográfica SHA256 determinista para detección de cambios.

    :param book: Instancia del modelo Book.
    :return: Tupla con (texto_normalizado, sha256_hash).
    """
    raw_title = (book.title or '').strip()
    norm_title = unicodedata.normalize('NFC', raw_title)

    author_name = (book.author.name if book.author else 'Desconocido').strip()
    norm_author = unicodedata.normalize('NFC', author_name)

    # Extraer categorías ordenadas alfabéticamente para consistencia determinista
    categories = sorted([c.name.strip() for c in book.categories.all() if c.name])
    categories_str = ', '.join(categories)

    # Limpieza exhaustiva de la sinopsis
    desc = (book.description or '').strip()
    # Eliminar posibles etiquetas HTML residuales
    clean_desc = re.sub(r'<[^>]+>', ' ', desc)
    # Colapsar espacios múltiples y saltos de línea redundantes
    clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
    norm_desc = unicodedata.normalize('NFC', clean_desc)
    # Límite seguro de caracteres para modelos de embedding
    truncated_desc = norm_desc[:2000]

    # Composición semántica estructurada
    genres_part = f"Géneros: {categories_str}." if categories_str else ""
    desc_part = f"Sinopsis: {truncated_desc}" if truncated_desc else ""

    parts = [f"Título: {norm_title}.", f"Autor: {norm_author}."]
    if genres_part:
        parts.append(genres_part)
    if desc_part:
        parts.append(desc_part)

    normalized_text = ' '.join(parts).strip()

    # Cálculo determinista del hash SHA256
    raw_hash_input = f"{norm_title}|{norm_author}|{categories_str}|{truncated_desc}"
    content_hash = hashlib.sha256(raw_hash_input.encode('utf-8')).hexdigest()

    return normalized_text, content_hash


def compute_book_content_hash(book: Book) -> str:
    """
    Helper de compatibilidad que retorna el hash SHA256 del contenido normalizado del libro.
    """
    _, content_hash = normalize_book_content_for_embedding(book)
    return content_hash


def generate_book_embedding(
    book: Book,
    force: bool = False,
    model_name: str | None = None,
) -> BookEmbedding:
    """
    Genera o actualiza el vector de embedding para una obra literaria, gobernando
    su ciclo de vida y garantizando el registro del modelo generador.

    :param book: Instancia del modelo Book.
    :param force: Si es True, fuerza el recálculo ignorando coincidencia de hash.
    :param model_name: Nombre explícito opcional del modelo de embedding.
    :return: Instancia de BookEmbedding actualizada.
    """
    ai_settings = get_ai_settings()
    active_model = model_name or ai_settings.model_embeddings
    content_to_embed, current_hash = normalize_book_content_for_embedding(book)

    record, _ = BookEmbedding.objects.get_or_create(
        book=book,
        defaults={
            'embedding_model': active_model,
            'embedding_status': EmbeddingStatus.PENDING,
            'content_hash': current_hash,
        },
    )

    # Si ya está completado, no hay cambios de contenido ni de modelo, y no se exige recálculo forzado
    if (
        not force
        and record.embedding_status == EmbeddingStatus.COMPLETED
        and record.content_hash == current_hash
        and record.embedding_model == active_model
        and record.vector
        and len(record.vector) > 0
    ):
        return record

    try:
        vector = get_embedding_for_text(content_to_embed)
        if vector and isinstance(vector, list) and len(vector) > 0:
            record.vector = vector
            record.dimension = len(vector)
            record.embedding_model = active_model
            record.embedding_version = 'v1.0'
            record.embedded_at = timezone.now()
            record.embedding_status = EmbeddingStatus.COMPLETED
            record.content_hash = current_hash
            record.save()
            return record
        else:
            record.embedding_status = EmbeddingStatus.FAILED
            record.save()
            return record
    except Exception as exc:
        logger.warning("Fallo al generar embedding para libro %s (%s): %s", book.id, book.title, exc)
        record.embedding_status = EmbeddingStatus.FAILED
        record.save()
        return record


def search_books_by_embedding(
    query_vector: list[float],
    limit: int = 20,
    min_similarity: float = 0.15,
    model_name: str | None = None,
    allowed_book_ids: set[int] | None = None,
) -> list[tuple[Book, float]]:
    """
    Búsqueda vectorial / ANN protegida contra mezcla de modelos incompatibles (Fase 25).
    Filtra rigurosamente por estado completado, modelo generador y dimensionalidad idéntica.

    :param query_vector: Vector numérico de la consulta.
    :param limit: Límite máximo de resultados a retornar.
    :param min_similarity: Umbral mínimo de similitud coseno.
    :param model_name: Modelo que originó el vector de consulta (para aislamiento estricto).
    :param allowed_book_ids: Conjunto opcional de IDs de libros permitidos (para facetado/filtros).
    :return: Lista de tuplas (Book, score_similitud) ordenada descendentemente.
    """
    if not query_vector or not isinstance(query_vector, list) or len(query_vector) == 0:
        return []

    ai_settings = get_ai_settings()
    target_model = model_name or ai_settings.model_embeddings
    query_dim = len(query_vector)

    # Filtrar estrictamente por modelo activo y longitud de vector para evitar mezcla incompatible
    qs = BookEmbedding.objects.filter(
        embedding_status=EmbeddingStatus.COMPLETED,
        embedding_model=target_model,
        dimension=query_dim,
    ).select_related('book', 'book__author').prefetch_related('book__categories')

    if allowed_book_ids is not None:
        qs = qs.filter(book_id__in=allowed_book_ids)

    results: list[tuple[Book, float]] = []

    for emb_rec in qs.iterator(chunk_size=100):
        candidate_vector = emb_rec.vector
        if candidate_vector and len(candidate_vector) == query_dim:
            sim = cosine_similarity(query_vector, candidate_vector)
            if sim >= min_similarity:
                results.append((emb_rec.book, float(sim)))

    results.sort(key=lambda item: item[1], reverse=True)
    return results[:limit]


def mark_stale_embeddings() -> int:
    """
    Inspecciona los libros con embeddings completados e identifica aquellos cuyo
    contenido ha sido modificado, transitando su estado a STALE para posterior reindexación.

    :return: Número de registros marcados como desactualizados.
    """
    stale_count = 0
    records = BookEmbedding.objects.filter(
        embedding_status=EmbeddingStatus.COMPLETED,
    ).select_related('book', 'book__author').prefetch_related('book__categories')

    for record in records.iterator(chunk_size=100):
        current_hash = compute_book_content_hash(record.book)
        if record.content_hash != current_hash:
            record.embedding_status = EmbeddingStatus.STALE
            record.save(update_fields=['embedding_status', 'updated_at'])
            stale_count += 1

    return stale_count


def reindex_all_embeddings(
    batch_size: int = 50,
    force: bool = False,
    model_name: str | None = None,
) -> dict[str, Any]:
    """
    Ejecuta el proceso por lotes para indexar o re-indexar obras literarias.
    Prioriza libros sin embedding, marcados como PENDING o STALE.

    :param batch_size: Tamaño de cada lote de procesamiento.
    :param force: Si es True, recalcula incluso los libros en estado COMPLETED.
    :param model_name: Modelo de embedding a utilizar.
    :return: Diccionario con estadísticas de la ejecución.
    """
    if force:
        books_qs = Book.objects.all().select_related('author').prefetch_related('categories')
    else:
        books_qs = (
            Book.objects.filter(
                embedding_record__isnull=True,
            )
            | Book.objects.filter(
                embedding_record__embedding_status__in=[
                    EmbeddingStatus.PENDING,
                    EmbeddingStatus.STALE,
                    EmbeddingStatus.FAILED,
                ],
            )
        ).distinct().select_related('author').prefetch_related('categories')

    total_candidates = books_qs.count()
    indexed_count = 0
    failed_count = 0

    for book in books_qs.iterator(chunk_size=batch_size):
        rec = generate_book_embedding(book, force=force, model_name=model_name)
        if rec.embedding_status == EmbeddingStatus.COMPLETED:
            indexed_count += 1
        else:
            failed_count += 1

    return {
        "candidates": total_candidates,
        "indexed": indexed_count,
        "failed": failed_count,
    }


def get_embedding_catalog_stats() -> dict[str, Any]:
    """
    Genera métricas de observabilidad sobre la cobertura y distribución de embeddings en el catálogo (Fase 25).

    :return: Diccionario con totales de catálogo, estado de embeddings y desglose por modelo/versión.
    """
    total_books = Book.objects.count()
    total_embeddings = BookEmbedding.objects.count()

    status_counts = {
        EmbeddingStatus.COMPLETED: 0,
        EmbeddingStatus.PENDING: 0,
        EmbeddingStatus.FAILED: 0,
        EmbeddingStatus.STALE: 0,
    }

    for item in BookEmbedding.objects.values('embedding_status').annotate(total=Count('id')):
        status_counts[item['embedding_status']] = item['total']

    completed = status_counts[EmbeddingStatus.COMPLETED]
    coverage_pct = round((completed / total_books) * 100, 2) if total_books > 0 else 0.0

    models_breakdown = list(
        BookEmbedding.objects.values(
            'embedding_model', 'embedding_version', 'dimension'
        ).annotate(count=Count('id')).order_by('-count')
    )

    ai_settings = get_ai_settings()

    return {
        "total_books": total_books,
        "total_embeddings": total_embeddings,
        "completed": completed,
        "pending": status_counts[EmbeddingStatus.PENDING],
        "failed": status_counts[EmbeddingStatus.FAILED],
        "stale": status_counts[EmbeddingStatus.STALE],
        "coverage_percentage": coverage_pct,
        "active_model": ai_settings.model_embeddings,
        "models_breakdown": models_breakdown,
    }

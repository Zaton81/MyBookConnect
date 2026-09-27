"""
Servicio para ciclo de vida, vectorización y re-embedding de libros (Fase 6 - Secciones 11.5 y 11.6).

Controla la generación de vectores, versionado, detección de cambios de contenido mediante
hashing SHA256 y reindexación selectiva o masiva por lotes.
"""

import hashlib
import logging
from typing import Any

from django.utils import timezone

from ai.config import get_ai_settings
from ai.embeddings import get_embedding_for_text
from books.models import Book, BookEmbedding, EmbeddingStatus

logger = logging.getLogger(__name__)


def compute_book_content_hash(book: Book) -> str:
    """
    Calcula la huella criptográfica SHA256 del contenido canónico de un libro.
    Permite detectar cambios en título, autor, categorías o sinopsis para invalidar
    selectivamente el vector y marcarlo como STALE sin recalcular innecesariamente.

    :param book: Instancia del libro a analizar.
    :return: Cadena hexadecimal de 64 caracteres.
    """
    author_name = book.author.name if book.author else ''
    categories_str = ','.join(sorted([c.name for c in book.categories.all()]))
    desc = (book.description or '').strip()

    raw_payload = f"{book.title.strip()}|{author_name.strip()}|{categories_str}|{desc}"
    return hashlib.sha256(raw_payload.encode('utf-8')).hexdigest()


def generate_book_embedding(
    book: Book,
    force: bool = False,
    model_name: str | None = None,
) -> BookEmbedding:
    """
    Genera o actualiza el vector de embedding para una obra literaria, gobernando
    su estado de ciclo de vida (COMPLETED, FAILED, STALE).

    :param book: Instancia del modelo Book.
    :param force: Si es True, fuerza la regeneración ignorando la caché de contenido.
    :param model_name: Nombre explícito opcional del modelo de embedding.
    :return: Instancia de BookEmbedding actualizada.
    """
    ai_settings = get_ai_settings()
    active_model = model_name or ai_settings.model_embeddings
    current_hash = compute_book_content_hash(book)

    record, _ = BookEmbedding.objects.get_or_create(
        book=book,
        defaults={
            'embedding_model': active_model,
            'embedding_status': EmbeddingStatus.PENDING,
            'content_hash': current_hash,
        },
    )

    # Si ya está completado y no hay cambios de contenido ni se exige recálculo forzado
    if (
        not force
        and record.embedding_status == EmbeddingStatus.COMPLETED
        and record.content_hash == current_hash
        and record.vector
        and len(record.vector) > 0
    ):
        return record

    # Construir texto semántico estructurado
    author_name = book.author.name if book.author else 'Desconocido'
    cat_names = [c.name for c in book.categories.all()]
    genres_text = f"Géneros: {', '.join(cat_names)}." if cat_names else ""
    desc_text = f"Sinopsis: {book.description[:1500]}" if book.description else ""

    content_to_embed = f"{book.title}. Autor: {author_name}. {genres_text} {desc_text}".strip()

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
        # Libros sin registro o con estado PENDING / STALE / FAILED
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

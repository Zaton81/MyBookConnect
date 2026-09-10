import logging

from celery import shared_task
from django.db.models import Avg

from .models import Author, Book, Review, UserBook
from .services import (
    ensure_book_cover,
    import_books_by_author,
    maybe_enrich_author,
    maybe_enrich_book,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def enrich_book_task(self, book_id: int) -> bool:
    """Enriquece metadatos y portada del libro en segundo plano."""
    try:
        book = Book.objects.filter(id=book_id).first()
        if not book:
            logger.warning(f"enrich_book_task: Libro {book_id} no encontrado")
            return False

        maybe_enrich_book(book)
        logger.info(f"enrich_book_task: Libro {book_id} ({book.title}) enriquecido con éxito")
        return True
    except Exception as exc:
        logger.warning(f"enrich_book_task error para libro {book_id}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def download_cover_task(self, book_id: int) -> bool:
    """Descarga y asocia la portada del libro en segundo plano."""
    try:
        book = Book.objects.filter(id=book_id).first()
        if not book:
            logger.warning(f"download_cover_task: Libro {book_id} no encontrado")
            return False

        ensure_book_cover(book)
        return bool(book.cover)
    except Exception as exc:
        logger.warning(f"download_cover_task error para libro {book_id}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_author_task(self, author_id: int) -> bool:
    """Enriquece biografía y fotografía del autor en segundo plano."""
    try:
        author = Author.objects.filter(id=author_id).first()
        if not author:
            logger.warning(f"refresh_author_task: Autor {author_id} no encontrado")
            return False

        maybe_enrich_author(author)
        logger.info(f"refresh_author_task: Autor {author_id} ({author.name}) actualizado")
        return True
    except Exception as exc:
        logger.warning(f"refresh_author_task error para autor {author_id}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def recalculate_book_rating_task(self, book_id: int) -> float | None:
    """Recalcula el promedio de calificaciones del libro de forma asíncrona."""
    try:
        book = Book.objects.filter(id=book_id).first()
        if not book:
            return None

        review_avg = Review.objects.filter(book=book, rating__isnull=False).aggregate(Avg('rating'))['rating__avg']
        if review_avg is not None:
            book.average_rating = round(review_avg, 2)
        else:
            ub_avg = UserBook.objects.filter(book=book, rating__isnull=False).aggregate(Avg('rating'))['rating__avg']
            book.average_rating = round(ub_avg, 2) if ub_avg else None

        book.save(update_fields=['average_rating'])
        logger.info(f"recalculate_book_rating_task: Libro {book_id} recalculado: {book.average_rating}")
        return book.average_rating
    except Exception as exc:
        logger.warning(f"recalculate_book_rating_task error para libro {book_id}: {exc}")
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def import_books_by_author_task(self, author_name: str) -> int:
    """Importa libros del autor de fuentes externas sin bloquear el hilo principal."""
    try:
        count = import_books_by_author(author_name)
        logger.info(f"import_books_by_author_task: {count} libros importados para '{author_name}'")
        return count
    except Exception as exc:
        logger.warning(f"import_books_by_author_task error para '{author_name}': {exc}")
        raise self.retry(exc=exc) from exc

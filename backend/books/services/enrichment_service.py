import logging
from datetime import datetime

import requests

from books.models import Book

from .base import DEFAULT_HEADERS, GOOGLE_BOOKS_API_URL, get_google_books_api_key
from .cover_service import ensure_book_cover

logger = logging.getLogger(__name__)


def enrich_book_metadata(book: Book) -> None:
    """
    Rellena la descripción y la fecha de publicación desde Google Books si faltan.
    """
    if book.description and book.published_date:
        return

    try:
        query = f'isbn:{book.isbn}' if book.isbn else book.title
        params = {'q': query, 'maxResults': 1, 'printType': 'books'}
        api_key = get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=7, headers=DEFAULT_HEADERS)
        if resp.ok:
            items = resp.json().get('items') or []
            if items:
                info = items[0].get('volumeInfo', {})
                changed = False
                if not book.description and info.get('description'):
                    book.description = info.get('description')
                    changed = True
                if not book.published_date and info.get('publishedDate'):
                    for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                        try:
                            dt = datetime.strptime(info.get('publishedDate'), fmt)
                            book.published_date = dt.date()
                            changed = True
                            break
                        except ValueError:
                            continue
                if changed:
                    book.save()
    except Exception as e:
        logger.warning(f"Error enriqueciendo metadatos del libro {book.title}: {e}")


def maybe_enrich_book(book: Book) -> None:
    """
    Enriquece portada y metadatos del libro (descripción, fecha) de forma exhaustiva.
    """
    ensure_book_cover(book)
    enrich_book_metadata(book)
    book.enrichment_attempted = True
    book.save(update_fields=['enrichment_attempted'])

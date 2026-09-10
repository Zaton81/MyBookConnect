import logging
import re

from django.core.cache import cache

logger = logging.getLogger(__name__)

# TTLs estandarizados en segundos
TTL_BOOK_DETAIL = 900          # 15 minutos
TTL_TRENDING = 900             # 15 minutos
TTL_EXTERNAL_API = 86400       # 24 horas
TTL_WIKIPEDIA_AUTHOR = 172800  # 48 horas


def _sanitize_key_part(value: str) -> str:
    """Normaliza texto para claves de caché seguras en Redis."""
    clean = re.sub(r'[\s:/?#\[\]@!$&\'()*+,;=]+', '_', value.strip().lower())
    return clean[:120]


def book_detail_key(book_id: int | str) -> str:
    """Namespace de detalle de libro: book:{id}"""
    return f"book:{book_id}"


def trending_key(period: str = 'all') -> str:
    """Namespace de libros populares/tendencias: trending:{period}"""
    return f"trending:{_sanitize_key_part(period)}"


def google_isbn_key(isbn: str) -> str:
    """Namespace de Google Books por ISBN: google:isbn:{isbn}"""
    clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip())
    return f"google:isbn:{clean_isbn}"


def google_search_key(query: str, offset: int = 0) -> str:
    """Namespace de búsqueda en Google Books: google:search:{query}:{offset}"""
    return f"google:search:{_sanitize_key_part(query)}:{offset}"


def openlibrary_isbn_key(isbn: str) -> str:
    """Namespace de OpenLibrary por ISBN: openlibrary:isbn:{isbn}"""
    clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip())
    return f"openlibrary:isbn:{clean_isbn}"


def openlibrary_work_key(work_id: str) -> str:
    """Namespace de OpenLibrary por Work ID: openlibrary:work:{id}"""
    return f"openlibrary:work:{_sanitize_key_part(work_id)}"


def openlibrary_search_key(query: str, page: int = 1) -> str:
    """Namespace de búsqueda en OpenLibrary: openlibrary:search:{query}:{page}"""
    return f"openlibrary:search:{_sanitize_key_part(query)}:{page}"


def wikipedia_author_key(author_name: str) -> str:
    """Namespace de autor en Wikipedia: wikipedia:author:{name}"""
    return f"wikipedia:author:{_sanitize_key_part(author_name)}"


def wikipedia_book_key(title: str) -> str:
    """Namespace de libro en Wikipedia: wikipedia:book:{title}"""
    return f"wikipedia:book:{_sanitize_key_part(title)}"


def invalidate_book_cache(book_id: int | str) -> None:
    """
    Invalida atómicamente la caché del detalle del libro y los rankings de tendencias dependientes.
    """
    try:
        key = book_detail_key(book_id)
        cache.delete(key)
        # Limpiar también tendencias ya que ratings y lectores pueden haber variado
        cache.delete(trending_key('all'))
        logger.debug(f"Caché invalidada para libro {book_id}")
    except Exception as exc:
        logger.warning(f"Error invalidando caché para libro {book_id}: {exc}")


def invalidate_trending_cache() -> None:
    """Invalida la caché del endpoint de tendencias."""
    try:
        cache.delete(trending_key('all'))
    except Exception as exc:
        logger.warning(f"Error invalidando caché de tendencias: {exc}")

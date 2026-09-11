"""
Servicios modulares de importación, enriquecimiento y gestión de proveedores para libros y autores.
"""

from .author_service import (
    maybe_enrich_author,
    maybe_enrich_author_from_openlibrary,
    maybe_enrich_author_from_wikidata,
    maybe_enrich_author_from_wikipedia,
)
from .base import (
    DEFAULT_HEADERS,
    GOOGLE_BOOKS_API_URL,
    OPEN_LIBRARY_AUTHORS_URL,
    OPEN_LIBRARY_COVERS_URL,
    OPEN_LIBRARY_SEARCH_URL,
    OPENLIBRARY_HEADERS,
    WIKIDATA_ENTITY_URL,
    WIKIDATA_SEARCH_URL,
    WIKIPEDIA_API_URL,
    WIKIPEDIA_OPENSEARCH_URL,
    BookProvider,
    ProviderAuthorData,
    ProviderBookData,
    get_google_books_api_key,
)
from .cover_service import (
    _attach_best_cover,
    _download_and_attach_image,
    attach_best_cover,
    download_and_attach_image,
    ensure_book_cover,
)
from .enrichment_service import (
    enrich_book_metadata,
    maybe_enrich_book,
)
from .import_service import (
    _create_or_get_from_volume,
    _import_books_by_author_from_wikipedia,
    _import_from_openlibrary_by_title,
    _import_from_wikipedia_by_title,
    import_books_by_author,
    import_multiple_by_title,
    import_single_by_query,
)
from .providers import (
    GoogleBooksProvider,
    OpenLibraryProvider,
    WikipediaProvider,
)
from .stats_service import get_user_reading_stats
from .trending_service import get_trending_books

__all__ = [
    # Funciones públicas principales
    'import_single_by_query',
    'import_multiple_by_title',
    'import_books_by_author',
    'get_trending_books',
    'maybe_enrich_author',
    'maybe_enrich_author_from_wikipedia',
    'maybe_enrich_author_from_wikidata',
    'maybe_enrich_author_from_openlibrary',
    'ensure_book_cover',
    'enrich_book_metadata',
    'maybe_enrich_book',
    'get_user_reading_stats',
    'download_and_attach_image',
    '_download_and_attach_image',
    'attach_best_cover',
    '_attach_best_cover',
    '_create_or_get_from_volume',
    '_import_books_by_author_from_wikipedia',
    '_import_from_openlibrary_by_title',
    '_import_from_wikipedia_by_title',
    'get_google_books_api_key',
    # Constantes
    'GOOGLE_BOOKS_API_URL',
    'OPEN_LIBRARY_SEARCH_URL',
    'OPEN_LIBRARY_AUTHORS_URL',
    'OPEN_LIBRARY_COVERS_URL',
    'WIKIPEDIA_API_URL',
    'WIKIPEDIA_OPENSEARCH_URL',
    'WIKIDATA_SEARCH_URL',
    'WIKIDATA_ENTITY_URL',
    'DEFAULT_HEADERS',
    'OPENLIBRARY_HEADERS',
    # Tipos y DTOs
    'ProviderBookData',
    'ProviderAuthorData',
    'BookProvider',
    # Proveedores
    'GoogleBooksProvider',
    'OpenLibraryProvider',
    'WikipediaProvider',
]

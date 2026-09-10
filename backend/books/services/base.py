from dataclasses import dataclass, field
from typing import Any, Protocol

from django.conf import settings

# URLs de APIs externas
GOOGLE_BOOKS_API_URL = 'https://www.googleapis.com/books/v1/volumes'
OPEN_LIBRARY_SEARCH_URL = 'https://openlibrary.org/search.json'
OPEN_LIBRARY_AUTHORS_URL = 'https://openlibrary.org/search/authors.json'
OPEN_LIBRARY_COVERS_URL = 'https://covers.openlibrary.org'
WIKIPEDIA_API_URL = 'https://{lang}.wikipedia.org/api/rest_v1/page/summary/'
WIKIPEDIA_OPENSEARCH_URL = 'https://{lang}.wikipedia.org/w/api.php'
WIKIDATA_SEARCH_URL = 'https://www.wikidata.org/w/api.php'
WIKIDATA_ENTITY_URL = 'https://www.wikidata.org/wiki/Special:EntityData/{entity}.json'

# Headers estándar para evitar bloqueos antibot (403 Wikimedia / Wikipedia)
DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

# Headers identificados obligatorios para la API de OpenLibrary
OPENLIBRARY_HEADERS = {
    'User-Agent': 'MyBookConnect/1.0 (https://github.com/Zaton81/MyBookConnect; contact@mybookconnect.com)',
    'Accept': 'application/json',
}


def get_google_books_api_key() -> str:
    """Obtiene la clave de Google Books configurada en settings o cadena vacía."""
    return getattr(settings, 'GOOGLE_BOOKS_API_KEY', '') or ''


@dataclass
class ProviderBookData:
    title: str
    author_name: str | None = None
    isbn: str | None = None
    description: str | None = None
    published_date_raw: str | None = None
    cover_url: str | None = None
    google_volume_id: str | None = None
    openlibrary_work_id: str | None = None
    openlibrary_edition_id: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderAuthorData:
    name: str
    biography: str | None = None
    photo_url: str | None = None
    openlibrary_author_id: str | None = None
    raw_payload: dict[str, Any] = field(default_factory=dict)


class BookProvider(Protocol):
    """Contrato que deben satisfacer todos los proveedores de libros."""

    def search_by_title(self, title: str, offset: int = 0, limit: int = 8) -> list[ProviderBookData]:
        ...

    def get_by_isbn(self, isbn: str) -> ProviderBookData | None:
        ...

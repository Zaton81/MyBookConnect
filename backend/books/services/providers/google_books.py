import logging

import requests

from ..base import DEFAULT_HEADERS, GOOGLE_BOOKS_API_URL, ProviderBookData, get_google_books_api_key

logger = logging.getLogger(__name__)


class GoogleBooksProvider:
    """Proveedor para consultar la API de Google Books v1."""

    def __init__(self, api_url: str = GOOGLE_BOOKS_API_URL):
        self.api_url = api_url

    def _parse_volume(self, volume: dict) -> ProviderBookData:
        info = volume.get('volumeInfo', {})
        google_vol_id = volume.get('id')
        title = info.get('title') or 'Desconocido'
        authors = info.get('authors') or []
        author_name = authors[0] if authors else None
        description = info.get('description')
        published_date_raw = info.get('publishedDate')

        # Extraer ISBN preferente
        isbn = None
        for ident in info.get('industryIdentifiers', []) or []:
            if ident.get('type') in ('ISBN_13', 'ISBN_10'):
                isbn = ident.get('identifier')
                break

        # Extraer URL de carátula
        image_links = info.get('imageLinks') or {}
        cover_url = None
        for key in ('extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail'):
            if image_links.get(key):
                cover_url = image_links.get(key)
                break

        return ProviderBookData(
            title=title,
            author_name=author_name,
            isbn=isbn,
            description=description,
            published_date_raw=published_date_raw,
            cover_url=cover_url,
            google_volume_id=google_vol_id,
            raw_payload=volume,
        )

    def search_by_title(self, title: str, offset: int = 0, limit: int = 8) -> list[ProviderBookData]:
        clean_title = title.strip()
        params = {
            'q': clean_title,
            'maxResults': limit,
            'startIndex': offset,
            'printType': 'books',
        }
        api_key = get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        try:
            resp = requests.get(self.api_url, params=params, timeout=7, headers=DEFAULT_HEADERS)
            if resp.status_code == 200:
                payload = resp.json()
                items = payload.get('items') or []
                return [self._parse_volume(item) for item in items]
            else:
                logger.warning(f"Google Books devolvió status {resp.status_code} para '{clean_title}'")
        except Exception as e:
            logger.warning(f"Error consultando Google Books para título '{clean_title}': {e}")

        return []

    def get_by_isbn(self, isbn: str) -> ProviderBookData | None:
        params = {'q': f'isbn:{isbn}', 'maxResults': 1, 'printType': 'books'}
        api_key = get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        try:
            resp = requests.get(self.api_url, params=params, timeout=8, headers=DEFAULT_HEADERS)
            if resp.ok:
                items = resp.json().get('items') or []
                if items:
                    data = self._parse_volume(items[0])
                    if not data.isbn:
                        data.isbn = isbn
                    return data
        except Exception as e:
            logger.warning(f"Error consultando Google Books para isbn {isbn}: {e}")

        return None

import logging

import requests

from ..base import (
    OPEN_LIBRARY_COVERS_URL,
    OPEN_LIBRARY_SEARCH_URL,
    OPENLIBRARY_HEADERS,
    ProviderBookData,
)

logger = logging.getLogger(__name__)


class OpenLibraryProvider:
    """Proveedor para consultar las APIs de OpenLibrary."""

    def __init__(
        self,
        search_url: str = OPEN_LIBRARY_SEARCH_URL,
        covers_url: str = OPEN_LIBRARY_COVERS_URL,
    ):
        self.search_url = search_url
        self.covers_url = covers_url

    def search_by_title(self, title: str, offset: int = 0, limit: int = 8) -> list[ProviderBookData]:
        clean_title = title.strip()
        page = 1 + (offset // limit if limit > 0 else 0)
        try:
            res = requests.get(
                self.search_url,
                params={'q': clean_title, 'page': page, 'limit': limit},
                timeout=8,
                headers=OPENLIBRARY_HEADERS,
            )
            if not res.ok:
                return []

            data = res.json()
            docs = data.get('docs') or []
            results: list[ProviderBookData] = []
            for doc in docs[:limit]:
                book_title = doc.get('title') or clean_title
                author_name = (doc.get('author_name') or [None])[0]
                cover_id = doc.get('cover_i')
                first_year = doc.get('first_publish_year')
                work_key = doc.get('key')
                edition_keys = doc.get('edition_key') or []
                edition_key = edition_keys[0] if edition_keys else None

                cover_url = None
                if cover_id:
                    cover_url = f'{self.covers_url}/b/id/{cover_id}-L.jpg'

                published_date_raw = str(first_year) if first_year else None

                results.append(
                    ProviderBookData(
                        title=book_title,
                        author_name=author_name,
                        isbn=None,
                        description=None,
                        published_date_raw=published_date_raw,
                        cover_url=cover_url,
                        openlibrary_work_id=work_key,
                        openlibrary_edition_id=edition_key,
                        raw_payload=doc,
                    )
                )
            return results
        except Exception as e:
            logger.warning(f"Error consultando OpenLibrary para título '{clean_title}': {e}")
            return []

    def get_by_isbn(self, isbn: str) -> ProviderBookData | None:
        try:
            ol_url = f'https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data'
            res = requests.get(ol_url, timeout=8, headers=OPENLIBRARY_HEADERS)
            if res.ok:
                data = res.json()
                book_info = data.get(f'ISBN:{isbn}')
                if book_info:
                    title = book_info.get('title') or 'Desconocido'
                    authors = book_info.get('authors') or []
                    author_name = authors[0].get('name') if authors else None
                    cover_url = book_info.get('cover', {}).get('large')
                    description = book_info.get('notes') or None
                    published_date_raw = book_info.get('publish_date')

                    return ProviderBookData(
                        title=title,
                        author_name=author_name,
                        isbn=isbn,
                        description=description,
                        published_date_raw=published_date_raw,
                        cover_url=cover_url,
                        raw_payload=book_info,
                    )
        except Exception as e:
            logger.warning(f"Error consultando OpenLibrary para isbn {isbn}: {e}")

        return None

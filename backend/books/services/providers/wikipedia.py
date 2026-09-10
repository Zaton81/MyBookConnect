import logging
import re

import requests

from ..base import DEFAULT_HEADERS, WIKIPEDIA_API_URL, WIKIPEDIA_OPENSEARCH_URL, ProviderBookData

logger = logging.getLogger(__name__)


class WikipediaProvider:
    """Proveedor para consultar la API de Wikipedia en español e inglés."""

    def __init__(self, lang: str = 'es'):
        self.lang = lang

    def search_by_title(self, title: str, offset: int = 0, limit: int = 5) -> list[ProviderBookData]:
        clean_title = title.strip()
        books: list[ProviderBookData] = []
        try:
            search_url = WIKIPEDIA_OPENSEARCH_URL.format(lang=self.lang)
            search_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': f'{clean_title} libro OR novela OR literatura',
                'format': 'json',
                'srlimit': limit,
            }
            r = requests.get(search_url, params=search_params, timeout=6, headers=DEFAULT_HEADERS)
            if not r.ok:
                return []

            search_results = r.json().get('query', {}).get('search', [])
            for item in search_results:
                page_title = item.get('title')
                if not page_title:
                    continue

                if any(term in page_title.lower() for term in ['película', 'serie', 'parque', 'álbum']):
                    continue

                summary_url = WIKIPEDIA_API_URL.format(lang=self.lang) + requests.utils.quote(page_title)
                sr = requests.get(summary_url, timeout=6, headers=DEFAULT_HEADERS)
                if not sr.ok:
                    continue

                data = sr.json()
                description = data.get('description', '').lower()
                if not any(term in description for term in ['novela', 'libro', 'obra', 'cuento', 'poema', 'ensayo', 'trilogía', 'publicación']):
                    continue

                book_title = data.get('title') or page_title
                synopsis = data.get('extract') or ''

                author_name = None
                desc_match = re.search(r'(?:de|por)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)', data.get('description', ''))
                if desc_match:
                    author_name = desc_match.group(1).strip()

                img_info = data.get('originalimage') or data.get('thumbnail') or {}
                cover_url = img_info.get('source')

                books.append(
                    ProviderBookData(
                        title=book_title,
                        author_name=author_name,
                        description=synopsis[:2000] if synopsis else None,
                        cover_url=cover_url,
                        raw_payload=data,
                    )
                )
        except Exception as e:
            logger.warning(f"Error consultando Wikipedia para '{clean_title}': {e}")

        return books

    def get_by_isbn(self, isbn: str) -> ProviderBookData | None:
        return None

    def search_books_by_author(self, author_name: str, limit: int = 8) -> list[ProviderBookData]:
        clean_author = author_name.strip()
        books: list[ProviderBookData] = []
        try:
            sr_params = {
                'action': 'query',
                'list': 'search',
                'srsearch': f'"{clean_author}" novela OR libro',
                'format': 'json',
                'srlimit': limit,
            }
            res = requests.get(WIKIPEDIA_OPENSEARCH_URL.format(lang=self.lang), params=sr_params, timeout=7, headers=DEFAULT_HEADERS)
            if res.ok:
                items = res.json().get('query', {}).get('search', [])
                for item in items:
                    page_title = item.get('title', '')
                    if not page_title:
                        continue
                    if page_title.strip().casefold() == clean_author.casefold():
                        continue

                    clean_title = re.sub(r'\s*\([^)]+\)$', '', page_title).strip()
                    sum_url = WIKIPEDIA_API_URL.format(lang=self.lang) + requests.utils.quote(page_title)
                    sum_res = requests.get(sum_url, timeout=7, headers=DEFAULT_HEADERS)
                    if sum_res.ok:
                        data = sum_res.json()
                        desc = data.get('description', '').lower()
                        if any(term in desc for term in ['desambiguación', 'escritor', 'biografía', 'persona']):
                            continue

                        synopsis = data.get('extract')
                        img_info = data.get('originalimage') or data.get('thumbnail') or {}
                        cover_url = img_info.get('source')

                        books.append(
                            ProviderBookData(
                                title=clean_title,
                                author_name=clean_author,
                                description=synopsis[:2000] if synopsis else None,
                                cover_url=cover_url,
                                raw_payload=data,
                            )
                        )
        except Exception as e:
            logger.warning(f"Error consultando libros de autor '{clean_author}' en Wikipedia: {e}")

        return books

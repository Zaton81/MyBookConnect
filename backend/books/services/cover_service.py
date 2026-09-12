import logging
import re

import requests
from django.core.files.base import ContentFile
from django.utils.text import slugify

from books.models import Book

from .base import DEFAULT_HEADERS, GOOGLE_BOOKS_API_URL, OPEN_LIBRARY_COVERS_URL, get_google_books_api_key

logger = logging.getLogger(__name__)


def _is_valid_image(content: bytes, content_type: str) -> bool:
    """Verifica si el contenido binario corresponde a una imagen válida."""
    if content_type and content_type.startswith('image/'):
        return True
    if content.startswith(b'\xff\xd8\xff'):  # JPEG
        return True
    if content.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
        return True
    if content.startswith(b'RIFF') and b'WEBP' in content[:16]:  # WebP
        return True
    if content.startswith((b'GIF87a', b'GIF89a')):  # GIF
        return True
    return False


def download_and_attach_image(instance, field_name: str, url: str, filename_hint: str) -> bool:
    """
    Descarga una imagen de forma segura con headers de navegador y la adjunta al modelo.
    Garantiza que URLs HTTP se actualicen a HTTPS y evita bloqueos antibot.
    """
    if not url:
        return False

    # Forzar HTTPS y limpiar parámetros problemáticos de Google Books
    if url.startswith('http://'):
        url = 'https://' + url[7:]
    url = url.replace('&edge=curl', '').replace('&edge=curl&', '&')

    try:
        r = requests.get(url, timeout=8, headers=DEFAULT_HEADERS, allow_redirects=True)
        r.raise_for_status()

        content = r.content
        if len(content) < 200:
            logger.warning(f"Imagen descargada es muy pequeña ({len(content)} bytes), ignorando")
            return False

        content_type = r.headers.get('Content-Type', '')
        if not _is_valid_image(content, content_type):
            logger.warning(f"URL no devolvió una imagen válida. Content-Type: {content_type}")
            return False

        # Limpiar nombre de archivo de caracteres especiales o parámetros
        clean_hint = re.sub(r'[?&].*$', '', filename_hint)
        if not clean_hint.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            clean_hint += '.jpg'

        # Sanitizar y validar imagen eliminando metadatos EXIF e inspeccionando integridad
        from mybookconnect.media_security import sanitize_image, validate_author_photo, validate_cover_image

        raw_file = ContentFile(content, name=clean_hint)
        try:
            if field_name == 'photo':
                validate_author_photo(raw_file)
            else:
                validate_cover_image(raw_file)
            clean_file = sanitize_image(raw_file, filename=clean_hint)
        except Exception as val_err:
            logger.warning(f"La imagen descargada desde {url} no superó la validación o sanitización: {val_err}")
            return False

        getattr(instance, field_name).save(clean_hint, clean_file, save=True)
        logger.info(f"Imagen sanitizada y guardada exitosamente en {field_name}: {clean_hint}")
        return True
    except Exception as e:
        logger.warning(f"Error descargando imagen desde {url}: {e}")
        return False


# Alias retrocompatible con código interno
_download_and_attach_image = download_and_attach_image


def attach_best_cover(book: Book, info: dict, isbn: str | None) -> None:
    """
    Obtiene la mejor carátula disponible desde Google Books u OpenLibrary.
    """
    # 1. Intentar con imageLinks de Google Books (forzando HTTPS y sin curl)
    image_links = info.get('imageLinks') or {}
    for key in ('extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail'):
        url = image_links.get(key)
        if url:
            if download_and_attach_image(
                instance=book,
                field_name='cover',
                url=url,
                filename_hint=f"{slugify(book.title)}-{book.id}.jpg",
            ):
                return

    # 2. Intentar OpenLibrary por ISBN si existe con ?default=false
    if isbn:
        for size in ('-L', '-M'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{isbn}{size}.jpg?default=false'
            if download_and_attach_image(
                instance=book,
                field_name='cover',
                url=ol_url,
                filename_hint=f"{slugify(book.title)}-{book.id}{size}.jpg",
            ):
                return


_attach_best_cover = attach_best_cover


def ensure_book_cover(book: Book) -> None:
    if book.cover:
        return

    # 1. Consulta directa por google_volume_id si está disponible
    if book.google_volume_id:
        try:
            vol_url = f"{GOOGLE_BOOKS_API_URL}/{book.google_volume_id}"
            resp = requests.get(vol_url, timeout=7, headers=DEFAULT_HEADERS)
            if resp.ok:
                vol_info = resp.json().get('volumeInfo', {})
                attach_best_cover(book, vol_info, book.isbn)
                if book.cover:
                    return
        except Exception as e:
            logger.warning(f"Error consultando google_volume_id {book.google_volume_id}: {e}")

    # 2. Consulta a OpenLibrary por ISBN con ?default=false
    if book.isbn:
        for size in ('-L', '-M'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{book.isbn}{size}.jpg?default=false'
            if download_and_attach_image(book, 'cover', ol_url, f"{slugify(book.title)}-{book.id}{size}.jpg"):
                return

    # 3. Búsqueda en Google Books (ISBN o Título + Autor)
    try:
        if book.isbn:
            query = f'isbn:{book.isbn}'
        elif book.author and book.author.name:
            query = f'intitle:"{book.title}" inauthor:"{book.author.name}"'
        else:
            query = book.title

        params = {'q': query, 'maxResults': 1, 'printType': 'books'}
        api_key = get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=7, headers=DEFAULT_HEADERS)
        if resp.ok:
            items = resp.json().get('items') or []
            if items:
                attach_best_cover(book, items[0].get('volumeInfo', {}), book.isbn)
                if book.cover:
                    return
    except Exception as e:
        logger.warning(f"Error asegurando portada en Google Books para {book.title}: {e}")

    # 4. Fallback a Wikipedia en español
    try:
        from .providers.wikipedia import WikipediaProvider
        wiki = WikipediaProvider(lang='es')
        wiki_items = wiki.search_by_title(book.title, limit=3)
        for item in wiki_items:
            if item.cover_url:
                if download_and_attach_image(book, 'cover', item.cover_url, f"{slugify(book.title)}-{book.id}-wiki.jpg"):
                    return
    except Exception as e:
        logger.warning(f"Fallback Wikipedia error para portada de {book.title}: {e}")

    # 5. Fallback a OpenLibrary por búsqueda de título
    try:
        from .base import OPEN_LIBRARY_SEARCH_URL, OPENLIBRARY_HEADERS
        ol_params = {'title': book.title, 'limit': 3}
        if book.author and book.author.name:
            ol_params['author'] = book.author.name
        resp = requests.get(OPEN_LIBRARY_SEARCH_URL, params=ol_params, headers=OPENLIBRARY_HEADERS, timeout=6)
        if resp.ok:
            docs = resp.json().get('docs', [])
            for doc in docs:
                cover_i = doc.get('cover_i')
                if cover_i:
                    ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/id/{cover_i}-L.jpg?default=false'
                    if download_and_attach_image(book, 'cover', ol_url, f"{slugify(book.title)}-{book.id}-ol.jpg"):
                        return
                doc_isbns = doc.get('isbn', [])
                if doc_isbns:
                    ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{doc_isbns[0]}-L.jpg?default=false'
                    if download_and_attach_image(book, 'cover', ol_url, f"{slugify(book.title)}-{book.id}-ol.jpg"):
                        return
    except Exception as e:
        logger.warning(f"Fallback OpenLibrary búsqueda error para portada de {book.title}: {e}")

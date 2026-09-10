import logging
import re

import requests
from django.core.files.base import ContentFile
from django.utils.text import slugify

from books.models import Book

from .base import DEFAULT_HEADERS, GOOGLE_BOOKS_API_URL, OPEN_LIBRARY_COVERS_URL, get_google_books_api_key

logger = logging.getLogger(__name__)


def download_and_attach_image(instance, field_name: str, url: str, filename_hint: str) -> bool:
    """
    Descarga una imagen de forma segura con headers de navegador y la adjunta al modelo.
    Garantiza que URLs HTTP se actualicen a HTTPS y evita bloqueos antibot.
    """
    if not url:
        return False

    # Forzar HTTPS si es posible
    if url.startswith('http://'):
        url = 'https://' + url[7:]

    try:
        r = requests.get(url, timeout=4, headers=DEFAULT_HEADERS, allow_redirects=True)
        r.raise_for_status()

        content_type = r.headers.get('Content-Type', '')
        if content_type and not content_type.startswith('image/'):
            logger.warning(f"URL no devolvió una imagen válida. Content-Type: {content_type}")
            return False

        content = r.content
        if len(content) < 100:
            logger.warning(f"Imagen descargada es muy pequeña ({len(content)} bytes), ignorando")
            return False

        # Limpiar nombre de archivo de caracteres especiales o parámetros
        clean_hint = re.sub(r'[?&].*$', '', filename_hint)
        if not clean_hint.endswith(('.jpg', '.jpeg', '.png', '.webp')):
            clean_hint += '.jpg'

        getattr(instance, field_name).save(clean_hint, ContentFile(content), save=True)
        logger.info(f"Imagen guardada exitosamente en {field_name}: {clean_hint}")
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
    # 1. Intentar con imageLinks de Google Books (forzando HTTPS)
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

    # 2. Intentar OpenLibrary por ISBN si existe
    if isbn:
        for size in ('-L', '-M'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{isbn}{size}.jpg'
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

    if book.isbn:
        for size in ('-L', '-M'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{book.isbn}{size}.jpg'
            if download_and_attach_image(book, 'cover', ol_url, f"{slugify(book.title)}-{book.id}{size}.jpg"):
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
                attach_best_cover(book, items[0].get('volumeInfo', {}), book.isbn)
    except Exception as e:
        logger.warning(f"Error asegurando portada para {book.title}: {e}")

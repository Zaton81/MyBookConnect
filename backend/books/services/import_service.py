import logging
import re
from datetime import datetime

from django.utils.text import slugify

from books.models import Author, Book

from .author_service import maybe_enrich_author
from .base import (
    DEFAULT_HEADERS,
    GOOGLE_BOOKS_API_URL,
    get_google_books_api_key,
)
from .cover_service import attach_best_cover, download_and_attach_image
from .providers.google_books import GoogleBooksProvider
from .providers.openlibrary import OpenLibraryProvider
from .providers.wikipedia import WikipediaProvider

logger = logging.getLogger(__name__)


def _create_or_get_from_volume(volume: dict, fallback_isbn: str | None = None) -> Book:
    """
    Crea o recupera un libro a partir de la estructura de volumen devuelta por Google Books.
    Aplica deduplicación multi-nivel por google_volume_id, isbn y (título, autor).
    """
    google_vol_id = volume.get('id')
    if google_vol_id:
        existing_vol = Book.objects.filter(google_volume_id=google_vol_id).first()
        if existing_vol:
            return existing_vol

    info = volume.get('volumeInfo', {})
    isbn = fallback_isbn
    for ident in info.get('industryIdentifiers', []) or []:
        if ident.get('type') in ('ISBN_13', 'ISBN_10'):
            isbn = ident.get('identifier')
            break

    if isbn:
        clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip())
        existing = Book.objects.filter(isbn=clean_isbn).first()
        if existing:
            if google_vol_id and not existing.google_volume_id:
                existing.google_volume_id = google_vol_id
                existing.save(update_fields=['google_volume_id'])
            return existing

    author_obj = None
    authors_list = info.get('authors') or []
    if authors_list:
        author_name = authors_list[0]
        author_obj, _ = Author.objects.get_or_create(name=author_name)

    title = info.get('title') or 'Desconocido'

    # Comprobar si ya existe con este título y autor
    existing = Book.objects.filter(title__iexact=title)
    if author_obj:
        existing = existing.filter(author=author_obj)
    found = existing.first()
    if found:
        updated_fields = []
        if isbn and not found.isbn:
            found.isbn = isbn
            updated_fields.append('isbn')
        if google_vol_id and not found.google_volume_id:
            found.google_volume_id = google_vol_id
            updated_fields.append('google_volume_id')
        if updated_fields:
            found.save(update_fields=updated_fields)
        return found

    book = Book(
        title=title,
        author=author_obj,
        isbn=isbn,
        google_volume_id=google_vol_id,
        description=info.get('description'),
    )
    published = info.get('publishedDate')
    if published:
        for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
            try:
                dt = datetime.strptime(published, fmt)
                book.published_date = dt.date()
                break
            except ValueError:
                continue
    book.save()
    attach_best_cover(book=book, info=info, isbn=isbn)
    return book


def import_single_by_query(query_isbn: str) -> Book | None:
    """
    Importa un libro específico mediante su ISBN consultando Google Books u OpenLibrary.
    """
    clean_isbn = re.sub(r'[^\dX]', '', query_isbn.upper().strip())
    existing = Book.objects.filter(isbn=clean_isbn).first()
    if existing:
        return existing

    # 1. Google Books Provider
    try:
        gb_provider = GoogleBooksProvider()
        book_data = gb_provider.get_by_isbn(clean_isbn)
        if book_data and book_data.raw_payload:
            return _create_or_get_from_volume(book_data.raw_payload, fallback_isbn=clean_isbn)
    except Exception as e:
        logger.warning(f"Error consultando Google Books para isbn {clean_isbn}: {e}")

    # 2. Fallback por ISBN en OpenLibrary
    try:
        ol_provider = OpenLibraryProvider()
        ol_data = ol_provider.get_by_isbn(clean_isbn)
        if ol_data:
            author_obj = None
            if ol_data.author_name:
                author_obj, _ = Author.objects.get_or_create(name=ol_data.author_name)

            book = Book.objects.create(
                title=ol_data.title,
                author=author_obj,
                isbn=clean_isbn,
                description=ol_data.description,
            )
            if ol_data.cover_url:
                download_and_attach_image(book, 'cover', ol_data.cover_url, f"{slugify(book.title)}-{book.id}.jpg")
            return book
    except Exception as e:
        logger.warning(f"Error consultando OpenLibrary para isbn {clean_isbn}: {e}")

    return None


def _import_from_wikipedia_by_title(title: str) -> list[Book]:
    """
    Busca e importa libros desde la API REST de Wikipedia en español e inglés.
    """
    books = []
    wiki_provider = WikipediaProvider(lang='es')
    items = wiki_provider.search_by_title(title, limit=5)

    for item in items:
        author_obj = None
        if item.author_name:
            author_obj, _ = Author.objects.get_or_create(name=item.author_name)

        existing = Book.objects.filter(title__iexact=item.title)
        if author_obj:
            existing = existing.filter(author=author_obj)
        existing_book = existing.first()
        if existing_book:
            books.append(existing_book)
            continue

        new_book = Book.objects.create(
            title=item.title,
            author=author_obj,
            description=item.description,
        )

        if item.cover_url:
            download_and_attach_image(
                instance=new_book,
                field_name='cover',
                url=item.cover_url,
                filename_hint=f"{slugify(new_book.title)}-{new_book.id}.jpg",
            )

        books.append(new_book)

    return books


def _import_from_openlibrary_by_title(title: str, offset: int = 0) -> list[Book]:
    """
    Busca e importa libros desde OpenLibrary.
    """
    ol_provider = OpenLibraryProvider()
    items = ol_provider.search_by_title(title, offset=offset, limit=6)
    results = []

    for item in items:
        book = None
        if item.openlibrary_work_id:
            book = Book.objects.filter(openlibrary_work_id=item.openlibrary_work_id).first()
        if not book and item.openlibrary_edition_id:
            book = Book.objects.filter(openlibrary_edition_id=item.openlibrary_edition_id).first()

        author_obj = None
        if item.author_name:
            author_obj, _ = Author.objects.get_or_create(name=item.author_name)

        if not book:
            existing = Book.objects.filter(title__iexact=item.title)
            if author_obj:
                existing = existing.filter(author=author_obj)
            book = existing.first()

        if not book:
            book = Book(
                title=item.title,
                author=author_obj,
                isbn=None,
                description=None,
                openlibrary_work_id=item.openlibrary_work_id,
                openlibrary_edition_id=item.openlibrary_edition_id,
            )
            if item.published_date_raw:
                try:
                    book.published_date = datetime.strptime(item.published_date_raw, '%Y').date()
                except ValueError:
                    pass
            book.save()
        else:
            updated_fields = []
            if item.openlibrary_work_id and not book.openlibrary_work_id:
                book.openlibrary_work_id = item.openlibrary_work_id
                updated_fields.append('openlibrary_work_id')
            if item.openlibrary_edition_id and not book.openlibrary_edition_id:
                book.openlibrary_edition_id = item.openlibrary_edition_id
                updated_fields.append('openlibrary_edition_id')
            if updated_fields:
                book.save(update_fields=updated_fields)

        if item.cover_url and not book.cover:
            download_and_attach_image(
                instance=book,
                field_name='cover',
                url=item.cover_url,
                filename_hint=f"{slugify(book.title)}-{book.id}.jpg",
            )
        results.append(book)

    return results


def import_multiple_by_title(title: str, offset: int = 0) -> list[Book]:
    """
    Busca libros externamente con arquitectura multi-proveedor:
    1. Google Books (con soporte de API Key y langRestrict)
    2. Fallback a Wikipedia (búsqueda estructurada + sinopsis + portada oficial)
    3. Fallback a OpenLibrary
    """
    books = []
    clean_title = title.strip()

    # 1. Intentar Google Books
    try:
        gb_provider = GoogleBooksProvider()
        book_dtos = gb_provider.search_by_title(clean_title, offset=offset, limit=8)
        for dto in book_dtos:
            if dto.raw_payload:
                book = _create_or_get_from_volume(dto.raw_payload)
                if book and book not in books:
                    books.append(book)
    except Exception as e:
        logger.warning(f"Error consultando Google Books para título '{clean_title}': {e}")

    # 2. Si Google Books devolvió vacío (por cuota 429 o falta de resultados), fallback a Wikipedia
    if not books and offset == 0:
        logger.info(f"Iniciando fallback a Wikipedia para libro: {clean_title}")
        wiki_books = _import_from_wikipedia_by_title(clean_title)
        if wiki_books:
            books.extend(wiki_books)

    # 3. Fallback adicional a OpenLibrary si aún no hay resultados
    if not books:
        logger.info(f"Iniciando fallback a OpenLibrary para libro: {clean_title}")
        ol_books = _import_from_openlibrary_by_title(clean_title, offset=offset)
        if ol_books:
            books.extend(ol_books)

    return books


def _import_books_by_author_from_wikipedia(author: Author) -> int:
    """
    Busca obras notables y novelas del autor en Wikipedia cuando Google Books agota cuota o falla.
    """
    wiki_provider = WikipediaProvider(lang='es')
    items = wiki_provider.search_books_by_author(author.name, limit=8)
    count = 0

    for item in items:
        existing = Book.objects.filter(title__iexact=item.title, author=author).first()
        if existing:
            continue

        new_book = Book.objects.create(
            title=item.title,
            author=author,
            description=item.description,
        )
        count += 1

        if item.cover_url:
            download_and_attach_image(
                instance=new_book,
                field_name='cover',
                url=item.cover_url,
                filename_hint=f"{slugify(item.title)}-{new_book.id}.jpg",
            )

    return count


def import_books_by_author(author_name: str) -> int:
    """
    Importa libros de un autor usando Google Books y Wikipedia con enriquecimiento previo del autor.
    """
    clean_name = author_name.strip()
    author, _ = Author.objects.get_or_create(name=clean_name)
    maybe_enrich_author(author)
    count = 0

    # 1. Intentar Google Books con inauthor entrecomillado
    try:
        params = {'q': f'inauthor:"{clean_name}"', 'maxResults': 10, 'printType': 'books'}
        api_key = get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        import requests
        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=7, headers=DEFAULT_HEADERS)
        if resp.ok:
            items = resp.json().get('items') or []
            for volume in items:
                if _create_or_get_from_volume(volume):
                    count += 1
            if count > 0:
                return count
    except Exception as e:
        logger.warning(f"Error consultando Google Books para autor {clean_name}: {e}")

    # 2. Si Google Books devuelve 429 o 0 resultados, consultar Wikipedia
    wiki_count = _import_books_by_author_from_wikipedia(author)
    return wiki_count

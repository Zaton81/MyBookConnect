import logging
import re
from datetime import datetime

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.text import slugify

from books.models import Author, Book, normalize_title

from .author_service import maybe_enrich_author
from .base import (
    DEFAULT_HEADERS,
    GOOGLE_BOOKS_API_URL,
    ProviderBookData,
    get_google_books_api_key,
)
from .cover_service import attach_best_cover, download_and_attach_image
from .enrichment_service import attach_categories_to_book
from .providers.amazon import AmazonBooksProvider
from .providers.google_books import GoogleBooksProvider
from .providers.openlibrary import OpenLibraryProvider
from .providers.wikipedia import WikipediaProvider

logger = logging.getLogger(__name__)


def _create_or_get_from_volume(volume: dict, fallback_isbn: str | None = None) -> Book:
    """
    Crea o recupera un libro a partir de la estructura de volumen devuelta por Google Books.
    Aplica deduplicación multi-nivel por google_volume_id, isbn y (título, autor).
    """
    info = volume.get('volumeInfo', {})
    isbn = fallback_isbn
    for ident in info.get('industryIdentifiers', []) or []:
        if ident.get('type') in ('ISBN_13', 'ISBN_10'):
            isbn = ident.get('identifier')
            break

    google_vol_id = volume.get('id')
    clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip()) if isbn else None

    # Extraer número de páginas si está disponible
    page_count = None
    raw_pages = info.get('pageCount')
    if raw_pages is not None:
        try:
            page_count = int(raw_pages)
            if page_count <= 0:
                page_count = None
        except (ValueError, TypeError):
            page_count = None

    with transaction.atomic():
        if google_vol_id:
            existing_vol = Book.objects.select_for_update().filter(google_volume_id=google_vol_id).first()
            if existing_vol:
                updated_fields = []
                if page_count and not existing_vol.page_count:
                    existing_vol.page_count = page_count
                    updated_fields.append('page_count')
                if updated_fields:
                    existing_vol.save(update_fields=updated_fields)
                if not existing_vol.cover:
                    attach_best_cover(book=existing_vol, info=info, isbn=isbn)
                return existing_vol

        if clean_isbn:
            existing = Book.find_by_isbn(clean_isbn)
            if existing:
                updated_fields = []
                if google_vol_id and not existing.google_volume_id:
                    existing.google_volume_id = google_vol_id
                    updated_fields.append('google_volume_id')
                if page_count and not existing.page_count:
                    existing.page_count = page_count
                    updated_fields.append('page_count')
                if updated_fields:
                    existing.save(update_fields=updated_fields)
                if not existing.cover:
                    attach_best_cover(book=existing, info=info, isbn=isbn)
                return existing

        author_obj = None
        authors_list = info.get('authors') or []
        if authors_list:
            author_name = authors_list[0]
            try:
                with transaction.atomic():
                    author_obj, _ = Author.objects.get_or_create(name=author_name)
            except IntegrityError:
                author_obj = Author.objects.filter(name=author_name).first()

        title = info.get('title') or 'Desconocido'

        # Comprobar si ya existe con este título y autor (unificando ediciones con distinto ISBN)
        norm_title = normalize_title(title)
        found = None
        if author_obj:
            candidates = Book.objects.select_for_update().filter(author=author_obj)
            for c in candidates:
                if normalize_title(c.title) == norm_title:
                    found = c
                    break
        elif norm_title:
            candidates = Book.objects.select_for_update().filter(title__iexact=title)
            found = candidates.first()

        if found:
            updated_fields = []
            had_no_isbn = not bool(found.isbn)
            if clean_isbn and found.add_isbn(clean_isbn):
                if had_no_isbn:
                    updated_fields.append('isbn')
                updated_fields.append('additional_isbns')
            if google_vol_id and not found.google_volume_id:
                found.google_volume_id = google_vol_id
                updated_fields.append('google_volume_id')
            if page_count and not found.page_count:
                found.page_count = page_count
                updated_fields.append('page_count')
            if not found.description and info.get('description'):
                found.description = info.get('description')
                updated_fields.append('description')
            if updated_fields:
                found.save(update_fields=updated_fields)
            if not found.cover:
                attach_best_cover(book=found, info=info, isbn=isbn)

            if not found.categories.exists():
                raw_cats = info.get('categories') or []
                extracted_cats = []
                for cat in raw_cats:
                    if isinstance(cat, str):
                        for part in cat.split('/'):
                            p = part.strip()
                            if p and p not in extracted_cats:
                                extracted_cats.append(p)
                if extracted_cats:
                    attach_categories_to_book(found, extracted_cats)

            return found

        book = Book(
            title=title,
            author=author_obj,
            isbn=isbn,
            google_volume_id=google_vol_id,
            description=info.get('description'),
            page_count=page_count,
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

        try:
            with transaction.atomic():
                book.save()
        except IntegrityError:
            # Recuperar limpiamente ante colisión concurrente de inserción
            recovered = None
            if google_vol_id:
                recovered = Book.objects.select_for_update().filter(google_volume_id=google_vol_id).first()
            if not recovered and clean_isbn:
                recovered = Book.objects.select_for_update().filter(isbn=clean_isbn).first()
            if not recovered and author_obj:
                recovered = Book.objects.select_for_update().filter(title__iexact=title, author=author_obj).first()
            if recovered:
                return recovered
            raise

        attach_best_cover(book=book, info=info, isbn=isbn)

        # Hidratar categorías para libro recién creado
        raw_cats = info.get('categories') or []
        extracted_cats = []
        for cat in raw_cats:
            if isinstance(cat, str):
                for part in cat.split('/'):
                    p = part.strip()
                    if p and p not in extracted_cats:
                        extracted_cats.append(p)
        if extracted_cats:
            attach_categories_to_book(book, extracted_cats)

        return book


def _maybe_attach_amazon_buy_link(book: Book, data: ProviderBookData) -> None:
    """Si el proveedor trajo un enlace de afiliado o ASIN de Amazon, asocia la oferta al marketplace."""
    if not book or not data or not data.affiliate_url:
        return
    try:
        from books.marketplace_models import BookBuyLink
        tag = getattr(settings, 'AMAZON_PAAPI_TAG', '') or getattr(settings, 'AMAZON_AFFILIATE_TAG', 'mybooksocial-21')
        BookBuyLink.objects.get_or_create(
            book=book,
            merchant_name="Amazon",
            format="paperback",
            defaults={
                'url': data.affiliate_url,
                'merchant_type': 'online_retailer',
                'is_official': True,
                'is_affiliate': True,
                'affiliate_tag': tag,
            },
        )
    except Exception as exc:
        logger.debug(f"No se pudo asociar BookBuyLink de Amazon para '{book.title}': {exc}")


def _create_or_get_from_provider_data(data: ProviderBookData, fallback_isbn: str | None = None) -> Book | None:
    """
    Crea o recupera un libro a partir de un DTO ProviderBookData (Amazon, OpenLibrary, etc.).
    Aplica deduplicación multi-nivel por ISBN, título/autor, hidratación de páginas y enlace de afiliado.
    """
    if not data or not data.title:
        return None

    isbn = data.isbn or fallback_isbn
    clean_isbn = re.sub(r'[^\dX]', '', isbn.upper().strip()) if isbn else None
    title = data.title.strip()
    author_name = data.author_name.strip() if data.author_name else None

    with transaction.atomic():
        # 1. Deduplicación por ISBN
        if clean_isbn:
            existing = Book.find_by_isbn(clean_isbn)
            if existing:
                updated_fields = []
                if data.page_count and not existing.page_count:
                    existing.page_count = data.page_count
                    updated_fields.append('page_count')
                if not existing.description and data.description:
                    existing.description = data.description
                    updated_fields.append('description')
                if updated_fields:
                    existing.save(update_fields=updated_fields)
                if not existing.cover and data.cover_url:
                    download_and_attach_image(existing, 'cover', data.cover_url, f"{slugify(existing.title)}-{existing.id}.jpg")
                if data.categories:
                    attach_categories_to_book(existing, data.categories)
                _maybe_attach_amazon_buy_link(existing, data)
                return existing

        # 2. Resolver autor
        author_obj = None
        if author_name:
            try:
                with transaction.atomic():
                    author_obj, _ = Author.objects.get_or_create(name=author_name)
            except IntegrityError:
                author_obj = Author.objects.filter(name=author_name).first()

        # 3. Deduplicación por Título Normalizado y Autor
        norm_title = normalize_title(title)
        found = None
        if author_obj:
            candidates = Book.objects.select_for_update().filter(author=author_obj)
            for c in candidates:
                if normalize_title(c.title) == norm_title:
                    found = c
                    break
        elif norm_title:
            candidates = Book.objects.select_for_update().filter(title__iexact=title)
            found = candidates.first()

        if found:
            updated_fields = []
            if clean_isbn and found.add_isbn(clean_isbn):
                updated_fields.append('additional_isbns')
                if not found.isbn:
                    updated_fields.append('isbn')
            if data.page_count and not found.page_count:
                found.page_count = data.page_count
                updated_fields.append('page_count')
            if not found.description and data.description:
                found.description = data.description
                updated_fields.append('description')
            if updated_fields:
                found.save(update_fields=updated_fields)
            if not found.cover and data.cover_url:
                download_and_attach_image(found, 'cover', data.cover_url, f"{slugify(found.title)}-{found.id}.jpg")
            if data.categories:
                attach_categories_to_book(found, data.categories)
            _maybe_attach_amazon_buy_link(found, data)
            return found

        # 4. Crear nuevo libro
        book = Book(
            title=title,
            author=author_obj,
            isbn=clean_isbn or isbn,
            description=data.description,
            page_count=data.page_count,
            openlibrary_work_id=data.openlibrary_work_id,
            openlibrary_edition_id=data.openlibrary_edition_id,
        )
        if data.published_date_raw:
            for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                try:
                    dt = datetime.strptime(data.published_date_raw[:10], fmt)
                    book.published_date = dt.date()
                    break
                except ValueError:
                    continue

        try:
            with transaction.atomic():
                book.save()
        except IntegrityError:
            recovered = None
            if clean_isbn:
                recovered = Book.objects.select_for_update().filter(isbn=clean_isbn).first()
            if not recovered and author_obj:
                recovered = Book.objects.select_for_update().filter(title__iexact=title, author=author_obj).first()
            if recovered:
                return recovered
            raise

        if data.cover_url:
            download_and_attach_image(book, 'cover', data.cover_url, f"{slugify(book.title)}-{book.id}.jpg")
        if data.categories:
            attach_categories_to_book(book, data.categories)
        _maybe_attach_amazon_buy_link(book, data)
        return book


def import_single_by_query(query_isbn: str) -> Book | None:
    """
    Importa un libro específico mediante su ISBN con arquitectura multi-proveedor jerárquica:
    1. Amazon PA-API (Primer proveedor prioritario de afiliados)
    2. Google Books
    3. OpenLibrary
    """
    clean_isbn = re.sub(r'[^\dX]', '', query_isbn.upper().strip())
    with transaction.atomic():
        existing = Book.objects.select_for_update().filter(isbn=clean_isbn).first()
        if existing:
            return existing

    # 1. Amazon PA-API Provider (Prioridad 1)
    try:
        amazon_provider = AmazonBooksProvider()
        if amazon_provider.is_configured():
            amz_data = amazon_provider.get_by_isbn(clean_isbn)
            if amz_data:
                book = _create_or_get_from_provider_data(amz_data, fallback_isbn=clean_isbn)
                if book:
                    return book
    except Exception as e:
        logger.warning(f"Error consultando Amazon PA-API para isbn {clean_isbn}: {e}")

    # 2. Google Books Provider (Prioridad 2)
    try:
        gb_provider = GoogleBooksProvider()
        book_data = gb_provider.get_by_isbn(clean_isbn)
        if book_data and book_data.raw_payload:
            return _create_or_get_from_volume(book_data.raw_payload, fallback_isbn=clean_isbn)
    except Exception as e:
        logger.warning(f"Error consultando Google Books para isbn {clean_isbn}: {e}")

    # 3. Fallback por ISBN en OpenLibrary (Prioridad 3)
    try:
        ol_provider = OpenLibraryProvider()
        ol_data = ol_provider.get_by_isbn(clean_isbn)
        if ol_data:
            book = _create_or_get_from_provider_data(ol_data, fallback_isbn=clean_isbn)
            if book:
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
        with transaction.atomic():
            author_obj = None
            if item.author_name:
                author_obj, _ = Author.objects.get_or_create(name=item.author_name)

            chosen_title = item.title
            raw_desc = item.description or ''
            # Si el término buscado en español está en la sinopsis de Wikipedia (ej. El guardián entre el centeno para The Catcher in the Rye),
            # incorporar el título en español para permitir búsqueda bilingüe perfecta
            clean_search = title.strip()
            if clean_search.lower() != item.title.lower() and clean_search.lower() in raw_desc.lower():
                chosen_title = f"{clean_search.title()} ({item.title})"
            elif clean_search.lower() not in item.title.lower() and len(clean_search) > 4:
                raw_desc = f"Título de búsqueda: {clean_search}. {raw_desc}"

            existing = Book.objects.select_for_update().filter(title__iexact=chosen_title)
            if not existing.exists():
                existing = Book.objects.select_for_update().filter(title__iexact=item.title)
            if author_obj:
                existing = existing.filter(author=author_obj)
            existing_book = existing.first()
            if existing_book:
                books.append(existing_book)
                continue

            new_book = Book.objects.create(
                title=chosen_title,
                author=author_obj,
                description=raw_desc,
            )

            if item.cover_url:
                download_and_attach_image(
                    instance=new_book,
                    field_name='cover',
                    url=item.cover_url,
                    filename_hint=f"{slugify(new_book.title)}-{new_book.id}.jpg",
                )

            # Enriquecer libro con categorías y metadatos adicionales de forma proactiva
            try:
                from .enrichment_service import enrich_book_metadata
                enrich_book_metadata(new_book)
            except Exception as ee:
                logger.debug(f"Error enriqueciendo libro importado {new_book.id}: {ee}")

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
        with transaction.atomic():
            book = None
            if item.openlibrary_work_id:
                book = Book.objects.select_for_update().filter(openlibrary_work_id=item.openlibrary_work_id).first()
            if not book and item.openlibrary_edition_id:
                book = Book.objects.select_for_update().filter(openlibrary_edition_id=item.openlibrary_edition_id).first()

            author_obj = None
            if item.author_name:
                try:
                    with transaction.atomic():
                        author_obj, _ = Author.objects.get_or_create(name=item.author_name)
                except IntegrityError:
                    author_obj = Author.objects.filter(name=item.author_name).first()

            if not book:
                existing = Book.objects.select_for_update().filter(title__iexact=item.title)
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
            if item.categories and not book.categories.exists():
                attach_categories_to_book(book, item.categories)
            results.append(book)

    return results


def import_multiple_by_title(title: str, offset: int = 0) -> list[Book]:
    """
    Busca libros externamente con arquitectura multi-proveedor jerárquica:
    1. Amazon PA-API (Primer proveedor prioritario de afiliados)
    2. Google Books (con soporte de API Key y langRestrict)
    3. Fallback a Wikipedia (búsqueda estructurada + sinopsis + portada oficial)
    4. Fallback a OpenLibrary
    """
    books = []
    clean_title = title.strip()

    # 1. Intentar Amazon PA-API (Prioridad 1)
    try:
        amazon_provider = AmazonBooksProvider()
        if amazon_provider.is_configured():
            amz_dtos = amazon_provider.search_by_title(clean_title, offset=offset, limit=8)
            for dto in amz_dtos:
                book = _create_or_get_from_provider_data(dto)
                if book and book not in books:
                    books.append(book)
            if books:
                return books
    except Exception as e:
        logger.warning(f"Error consultando Amazon PA-API para título '{clean_title}': {e}")

    # 2. Intentar Google Books (Prioridad 2)
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
        with transaction.atomic():
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

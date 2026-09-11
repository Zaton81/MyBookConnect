import logging
from datetime import datetime

import requests
from django.utils.text import slugify

from books.models import Author, Book, Category

from .base import DEFAULT_HEADERS, GOOGLE_BOOKS_API_URL, get_google_books_api_key
from .cover_service import ensure_book_cover
from .providers.openlibrary import OpenLibraryProvider
from .providers.wikipedia import WikipediaProvider

logger = logging.getLogger(__name__)


def attach_categories_to_book(book: Book, category_names: list[str]) -> None:
    """
    Asocia de forma segura nombres de categorías/géneros literarios al libro.

    Parámetros:
        book (Book): Instancia del modelo Book a la que asociar las categorías.
        category_names (list[str]): Lista de cadenas con los nombres de categorías/géneros.

    Comportamiento:
        - Normaliza el nombre y genera o recupera el slug correspondiente.
        - Evita registros duplicados y respeta constraints de unicidad en la base de datos.
    """
    if not category_names:
        return
    for name in category_names:
        clean_name = str(name).strip()[:100]
        if not clean_name:
            continue
        slug = slugify(clean_name)[:100] or 'genero'
        try:
            category_obj = Category.objects.filter(name__iexact=clean_name).first()
            if not category_obj:
                category_obj = Category.objects.filter(slug=slug).first()
            if not category_obj:
                category_obj = Category.objects.create(name=clean_name, slug=slug)
            book.categories.add(category_obj)
        except Exception as e:
            logger.debug(f"Error asociando categoría '{clean_name}' a libro {book.id}: {e}")


def enrich_book_metadata(book: Book) -> None:
    """
    Rellena proactivamente cualquier campo faltante del libro:
    - Autor/autores (`author`)
    - Categorías/géneros (`categories`)
    - Sinopsis (`description`)
    - Fecha de publicación (`published_date`)
    - Portada (`cover`)

    Estrategia multi-proveedor en cascada:
    1. Google Books API (vía ISBN o título).
    2. OpenLibrary API (búsqueda por ISBN o título).
    3. Wikipedia API (búsqueda de sinopsis y autor en español).
    """
    has_author = book.author is not None
    has_categories = book.categories.exists()
    has_description = bool(book.description)
    has_published_date = bool(book.published_date)
    has_cover = bool(book.cover)

    # Si falta portada, intentar descargarla
    if not has_cover:
        try:
            ensure_book_cover(book)
            has_cover = bool(book.cover)
        except Exception as ce:
            logger.debug(f"No se pudo resolver portada inicial para {book.title}: {ce}")

    # Si todos los campos están presentes, no es necesario consultar APIs externas
    if has_author and has_categories and has_description and has_published_date and has_cover:
        return

    # 1. Intentar con Google Books
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
                info = items[0].get('volumeInfo', {})
                changed = False

                # Auto-relleno de autor si falta
                if not has_author and info.get('authors'):
                    authors = info.get('authors')
                    if isinstance(authors, list) and len(authors) > 0:
                        author_name = str(authors[0]).strip()
                        if author_name:
                            author_obj, _ = Author.objects.get_or_create(name=author_name)
                            book.author = author_obj
                            has_author = True
                            changed = True

                # Auto-relleno de sinopsis si falta
                if not has_description and info.get('description'):
                    book.description = info.get('description')
                    has_description = True
                    changed = True

                # Auto-relleno de fecha de publicación si falta
                if not has_published_date and info.get('publishedDate'):
                    for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                        try:
                            dt = datetime.strptime(info.get('publishedDate'), fmt)
                            book.published_date = dt.date()
                            has_published_date = True
                            changed = True
                            break
                        except ValueError:
                            continue

                if changed:
                    book.save()

                # Categorías de Google Books si faltan
                if not has_categories:
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
                        has_categories = book.categories.exists()
    except Exception as e:
        logger.warning(f"Error enriqueciendo metadatos con Google Books para {book.title}: {e}")

    # 2. Fallback con OpenLibrary si aún falta autor, descripción, fecha o categorías
    if not has_author or not has_description or not has_categories or not has_published_date:
        try:
            ol_provider = OpenLibraryProvider()
            ol_data = None
            if book.isbn:
                ol_data = ol_provider.get_by_isbn(book.isbn)
            if not ol_data and book.title:
                ol_results = ol_provider.search_by_title(book.title, limit=1)
                if ol_results:
                    ol_data = ol_results[0]

            if ol_data:
                changed = False
                if not has_author and ol_data.author_name:
                    author_name = str(ol_data.author_name).strip()
                    if author_name:
                        author_obj, _ = Author.objects.get_or_create(name=author_name)
                        book.author = author_obj
                        has_author = True
                        changed = True

                if not has_description and ol_data.description:
                    book.description = ol_data.description
                    has_description = True
                    changed = True

                if not has_published_date and ol_data.published_date_raw:
                    for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                        try:
                            dt = datetime.strptime(str(ol_data.published_date_raw).strip(), fmt)
                            book.published_date = dt.date()
                            has_published_date = True
                            changed = True
                            break
                        except ValueError:
                            continue

                if changed:
                    book.save()

                if not has_categories and ol_data.categories:
                    attach_categories_to_book(book, ol_data.categories)
                    has_categories = book.categories.exists()
        except Exception as e:
            logger.warning(f"Error consultando OpenLibrary para {book.title}: {e}")

    # 3. Fallback con Wikipedia si aún falta sinopsis o autor
    if not has_description or not has_author:
        try:
            wiki_provider = WikipediaProvider(lang='es')
            wiki_items = wiki_provider.search_by_title(book.title, limit=2)
            if wiki_items:
                best_wiki = wiki_items[0]
                changed = False
                if not has_description and best_wiki.description:
                    book.description = best_wiki.description
                    has_description = True
                    changed = True
                if not has_author and best_wiki.author_name:
                    author_name = str(best_wiki.author_name).strip()
                    if author_name:
                        author_obj, _ = Author.objects.get_or_create(name=author_name)
                        book.author = author_obj
                        has_author = True
                        changed = True
                if changed:
                    book.save()
        except Exception as e:
            logger.warning(f"Error consultando Wikipedia para sinopsis de {book.title}: {e}")

    # Si finalmente se completó autor pero este carece de biografía o foto, enriquecer autor
    if book.author and (not book.author.biography or not book.author.photo):
        try:
            from .author_service import maybe_enrich_author
            maybe_enrich_author(book.author)
        except Exception as e:
            logger.debug(f"Error enriqueciendo autor asociado '{book.author.name}': {e}")


def maybe_enrich_book(book: Book) -> None:
    """
    Enriquece de forma exhaustiva la portada y todos los metadatos de un libro
    (autor, categorías, sinopsis y fecha de publicación) marcando el intento.
    """
    ensure_book_cover(book)
    enrich_book_metadata(book)
    book.enrichment_attempted = True
    book.save(update_fields=['enrichment_attempted'])

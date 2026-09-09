import logging
import re
from datetime import datetime

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify

from .models import Author, Book

# URLs de APIs externas
GOOGLE_BOOKS_API_URL = 'https://www.googleapis.com/books/v1/volumes'
OPEN_LIBRARY_SEARCH_URL = 'https://openlibrary.org/search.json'
OPEN_LIBRARY_AUTHORS_URL = 'https://openlibrary.org/search/authors.json'
OPEN_LIBRARY_COVERS_URL = 'https://covers.openlibrary.org'
WIKIPEDIA_API_URL = 'https://{lang}.wikipedia.org/api/rest_v1/page/summary/'
WIKIPEDIA_OPENSEARCH_URL = 'https://{lang}.wikipedia.org/w/api.php'
WIKIDATA_SEARCH_URL = 'https://www.wikidata.org/w/api.php'
WIKIDATA_ENTITY_URL = 'https://www.wikidata.org/wiki/Special:EntityData/{entity}.json'

# Headers estándar válidos para evitar bloqueos antibot (ej. 403 de Wikimedia/Wikipedia)
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

logger = logging.getLogger(__name__)


def _get_google_books_api_key() -> str:
    return getattr(settings, 'GOOGLE_BOOKS_API_KEY', '') or ''


def import_single_by_query(query_isbn: str):
    """
    Importa un libro específico mediante su ISBN consultando Google Books u OpenLibrary.
    """
    clean_isbn = re.sub(r'[^\dX]', '', query_isbn.upper().strip())
    existing = Book.objects.filter(isbn=clean_isbn).first()
    if existing:
        return existing

    try:
        params = {'q': f'isbn:{clean_isbn}', 'maxResults': 1, 'printType': 'books'}
        api_key = _get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=8, headers=DEFAULT_HEADERS)
        if resp.ok:
            payload = resp.json()
            items = payload.get('items') or []
            if items:
                return _create_or_get_from_volume(items[0], fallback_isbn=clean_isbn)
    except Exception as e:
        logger.warning(f"Error consultando Google Books para isbn {clean_isbn}: {e}")

    # Fallback por ISBN en OpenLibrary
    try:
        ol_url = f'https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data'
        res = requests.get(ol_url, timeout=8, headers=DEFAULT_HEADERS)
        if res.ok:
            data = res.json()
            book_info = data.get(f'ISBN:{clean_isbn}')
            if book_info:
                title = book_info.get('title')
                authors = book_info.get('authors') or []
                author_obj = None
                if authors:
                    author_name = authors[0].get('name')
                    if author_name:
                        author_obj, _ = Author.objects.get_or_create(name=author_name)
                        maybe_enrich_author(author_obj)

                book = Book.objects.create(
                    title=title,
                    author=author_obj,
                    isbn=clean_isbn,
                    description=book_info.get('notes') or None,
                )
                cover_url = book_info.get('cover', {}).get('large')
                if cover_url:
                    _download_and_attach_image(book, 'cover', cover_url, f"{slugify(title)}-{book.id}.jpg")
                return book
    except Exception as e:
        logger.warning(f"Error consultando OpenLibrary para isbn {clean_isbn}: {e}")

    return None


def import_multiple_by_title(title: str, offset: int = 0):
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
        params = {
            'q': clean_title,
            'maxResults': 8,
            'startIndex': offset,
            'printType': 'books',
        }
        api_key = _get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=7, headers=DEFAULT_HEADERS)
        if resp.status_code == 200:
            payload = resp.json()
            items = payload.get('items') or []
            for volume in items:
                book = _create_or_get_from_volume(volume)
                if book and book not in books:
                    books.append(book)
        else:
            logger.warning(f"Google Books devolvió status {resp.status_code} para '{clean_title}'")
    except Exception as e:
        logger.warning(f"Error consultando Google Books para título '{clean_title}': {e}")

    # 2. Si Google Books devolvió 429 o vacíos, fallback a Wikipedia
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


def _import_from_wikipedia_by_title(title: str):
    """
    Busca e importa libros desde la API REST de Wikipedia en español e inglés.
    Wikipedia ofrece sinopsis completas, autores y portadas originales sin cuotas restrictivas.
    """
    books = []
    headers = DEFAULT_HEADERS

    try:
        search_url = 'https://es.wikipedia.org/w/api.php'
        search_params = {
            'action': 'query',
            'list': 'search',
            'srsearch': f'{title} libro OR novela OR literatura',
            'format': 'json',
            'srlimit': 5,
        }
        r = requests.get(search_url, params=search_params, timeout=6, headers=headers)
        if not r.ok:
            return []

        search_results = r.json().get('query', {}).get('search', [])
        for item in search_results:
            page_title = item.get('title')
            if not page_title:
                continue

            # Descartar artículos de películas, parques, etc. si hay especificación clara
            if any(term in page_title.lower() for term in ['película', 'serie', 'parque', 'álbum']):
                continue

            summary_url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(page_title)}"
            sr = requests.get(summary_url, timeout=6, headers=headers)
            if not sr.ok:
                continue

            data = sr.json()
            description = data.get('description', '').lower()
            # Validar que es una obra escrita
            if not any(term in description for term in ['novela', 'libro', 'obra', 'cuento', 'poema', 'ensayo', 'trilogía', 'publicación']):
                continue

            book_title = data.get('title') or page_title
            synopsis = data.get('extract') or ''

            # Extraer autor de la descripción si contiene "de <Autor>"
            author_name = None
            desc_match = re.search(r'(?:de|por)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)', data.get('description', ''))
            if desc_match:
                author_name = desc_match.group(1).strip()

            author_obj = None
            if author_name:
                author_obj, _ = Author.objects.get_or_create(name=author_name)
                maybe_enrich_author(author_obj)

            # Evitar duplicados por título y autor
            existing = Book.objects.filter(title__iexact=book_title)
            if author_obj:
                existing = existing.filter(author=author_obj)
            existing_book = existing.first()
            if existing_book:
                books.append(existing_book)
                continue

            new_book = Book.objects.create(
                title=book_title,
                author=author_obj,
                description=synopsis[:2000] if synopsis else None,
            )

            # Descargar portada de Wikimedia
            img_info = data.get('originalimage') or data.get('thumbnail') or {}
            img_url = img_info.get('source')
            if img_url:
                _download_and_attach_image(
                    instance=new_book,
                    field_name='cover',
                    url=img_url,
                    filename_hint=f"{slugify(new_book.title)}-{new_book.id}.jpg",
                )

            books.append(new_book)

    except Exception as e:
        logger.warning(f"Error importando desde Wikipedia para '{title}': {e}")

    return books


def _import_from_openlibrary_by_title(title: str, offset: int = 0):
    try:
        res = requests.get(
            OPEN_LIBRARY_SEARCH_URL,
            params={'title': title, 'offset': offset},
            timeout=8,
            headers=DEFAULT_HEADERS,
        )
        if not res.ok:
            return []

        data = res.json()
        docs = data.get('docs') or []
        results = []
        for doc in docs[:5]:
            book_title = doc.get('title') or title
            author_name = (doc.get('author_name') or [None])[0]
            cover_id = doc.get('cover_i')
            first_year = doc.get('first_publish_year')

            author_obj = None
            if author_name:
                author_obj, _ = Author.objects.get_or_create(name=author_name)
                maybe_enrich_author(author_obj)

            # Evitar crear duplicados
            existing = Book.objects.filter(title__iexact=book_title)
            if author_obj:
                existing = existing.filter(author=author_obj)
            book = existing.first()

            if not book:
                book = Book(
                    title=book_title,
                    author=author_obj,
                    isbn=None,
                    description=None,
                )
                if first_year:
                    try:
                        book.published_date = datetime.strptime(str(first_year), '%Y').date()
                    except ValueError:
                        pass
                book.save()

            if cover_id and not book.cover:
                ol_cover_url = f'{OPEN_LIBRARY_COVERS_URL}/b/id/{cover_id}-L.jpg'
                _download_and_attach_image(
                    instance=book,
                    field_name='cover',
                    url=ol_cover_url,
                    filename_hint=f"{slugify(book.title)}-{book.id}.jpg"
                )
            results.append(book)
        return results
    except Exception as e:
        logger.warning(f"OpenLibrary query failed: {e}")
        return []


def _create_or_get_from_volume(volume, fallback_isbn=None):
    info = volume.get('volumeInfo', {})
    isbn = fallback_isbn
    for ident in info.get('industryIdentifiers', []) or []:
        if ident.get('type') in ('ISBN_13', 'ISBN_10'):
            isbn = ident.get('identifier')
            break

    if isbn:
        existing = Book.objects.filter(isbn=isbn).first()
        if existing:
            return existing

    author_obj = None
    authors_list = info.get('authors') or []
    if authors_list:
        author_name = authors_list[0]
        author_obj, _ = Author.objects.get_or_create(name=author_name)
        maybe_enrich_author(author_obj)

    title = info.get('title') or 'Desconocido'

    # Comprobar si ya existe con este título y autor
    existing = Book.objects.filter(title__iexact=title)
    if author_obj:
        existing = existing.filter(author=author_obj)
    found = existing.first()
    if found:
        if isbn and not found.isbn:
            found.isbn = isbn
            found.save(update_fields=['isbn'])
        return found

    book = Book(
        title=title,
        author=author_obj,
        isbn=isbn,
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
    _attach_best_cover(book=book, info=info, isbn=isbn)
    return book


def _download_and_attach_image(instance, field_name: str, url: str, filename_hint: str):
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
        r = requests.get(url, timeout=10, headers=DEFAULT_HEADERS, allow_redirects=True)
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


def maybe_enrich_author(author: Author):
    """
    Enriquece de forma exhaustiva al autor:
    1. Wikipedia (biografía detallada en español y foto en alta resolución)
    2. Wikidata (como alternativa para retrato o biografía adicional)
    3. OpenLibrary (para fotos adicionales si aún faltan)
    """
    if author.biography and author.photo:
        return

    # 1. Wikipedia primero (más fiable y sin caídas de SSL)
    maybe_enrich_author_from_wikipedia(author)

    # 2. Wikidata si falta foto o bio
    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikidata(author)

    # 3. OpenLibrary si todavía falta algo
    if not author.biography or not author.photo:
        maybe_enrich_author_from_openlibrary(author)


def maybe_enrich_author_from_wikipedia(author: Author):
    """
    Enriquece la información del autor desde Wikipedia usando headers válidos.
    """
    if author.biography and author.photo:
        return

    name = author.name.strip()
    try:
        for lang in ('es', 'en'):
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            r = requests.get(url, timeout=7, headers=DEFAULT_HEADERS)
            if not r.ok:
                # Probar con opensearch
                sr = requests.get(
                    WIKIPEDIA_OPENSEARCH_URL.format(lang=lang),
                    params={'action': 'opensearch', 'search': name, 'limit': 3, 'format': 'json'},
                    timeout=7,
                    headers=DEFAULT_HEADERS,
                )
                if sr.ok:
                    titles = sr.json()[1] if len(sr.json()) > 1 else []
                    for t in titles:
                        sub_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(t)
                        sub_r = requests.get(sub_url, timeout=7, headers=DEFAULT_HEADERS)
                        if sub_r.ok:
                            r = sub_r
                            break

            if r.ok:
                data = r.json()
                desc = data.get('description', '').lower()
                # Verificar que sea persona o escritor
                if 'desambiguación' in desc or 'disambiguation' in desc:
                    continue

                if not author.biography:
                    extract = data.get('extract')
                    if extract:
                        author.biography = extract[:4000]

                if not author.photo:
                    img_data = data.get('originalimage') or data.get('thumbnail') or {}
                    img_url = img_data.get('source')
                    if img_url:
                        _download_and_attach_image(
                            instance=author,
                            field_name='photo',
                            url=img_url,
                            filename_hint=f"{slugify(author.name)}.jpg",
                        )

                if author.biography or author.photo:
                    author.save()
                    break

    except Exception as e:
        logger.warning(f"Error enriqueciendo {author.name} desde Wikipedia: {e}")


def maybe_enrich_author_from_wikidata(author: Author):
    """
    Enriquece autor desde Wikidata buscando retrato P18 y biografía.
    """
    if author.biography and author.photo:
        return

    try:
        search_params = {
            'action': 'wbsearchentities',
            'search': author.name,
            'language': 'es',
            'type': 'item',
            'format': 'json',
            'limit': 5,
        }
        search_resp = requests.get(WIKIDATA_SEARCH_URL, params=search_params, timeout=7, headers=DEFAULT_HEADERS)
        if not search_resp.ok:
            return

        results = search_resp.json().get('search', [])
        for item in results:
            entity_id = item.get('id')
            entity_url = WIKIDATA_ENTITY_URL.format(entity=entity_id)
            entity_resp = requests.get(entity_url, timeout=7, headers=DEFAULT_HEADERS)
            if not entity_resp.ok:
                continue

            entity_info = entity_resp.json().get('entities', {}).get(entity_id, {})
            claims = entity_info.get('claims', {})

            # Foto P18
            if not author.photo and 'P18' in claims:
                image_claims = claims['P18']
                if image_claims:
                    img_filename = image_claims[0].get('mainsnak', {}).get('datavalue', {}).get('value')
                    if img_filename:
                        clean_fn = img_filename.replace(' ', '_')
                        import hashlib
                        md5_hash = hashlib.md5(clean_fn.encode('utf-8')).hexdigest()
                        image_url = f"https://upload.wikimedia.org/wikipedia/commons/{md5_hash[0]}/{md5_hash[0:2]}/{requests.utils.quote(clean_fn)}"
                        _download_and_attach_image(
                            instance=author,
                            field_name='photo',
                            url=image_url,
                            filename_hint=f"{slugify(author.name)}_wikidata.jpg",
                        )

            # Descripción / Biografía
            if not author.biography:
                descriptions = entity_info.get('descriptions', {})
                desc = descriptions.get('es', {}).get('value') or descriptions.get('en', {}).get('value')
                if desc:
                    author.biography = f"{author.name}: {desc}"

            if author.biography or author.photo:
                author.save()
                break

    except Exception as e:
        logger.warning(f"Error enriqueciendo {author.name} desde Wikidata: {e}")


def maybe_enrich_author_from_openlibrary(author: Author):
    """
    Enriquece autor desde OpenLibrary como fallback secundario.
    """
    if author.biography and author.photo:
        return

    try:
        rs = requests.get(
            OPEN_LIBRARY_AUTHORS_URL,
            params={'q': author.name},
            timeout=8,
            headers=DEFAULT_HEADERS,
        )
        if not rs.ok:
            return

        docs = rs.json().get('docs') or []
        if not docs:
            return

        best = docs[0]
        olid = best.get('key')
        if olid and not author.biography:
            detail_url = f'https://openlibrary.org/authors/{olid.split("/")[-1]}.json'
            rd = requests.get(detail_url, timeout=6, headers=DEFAULT_HEADERS)
            if rd.ok:
                bio = rd.json().get('bio')
                if isinstance(bio, dict):
                    bio = bio.get('value')
                if bio:
                    author.biography = bio

        photos = best.get('photos') or []
        if photos and not author.photo:
            photo_url = f'{OPEN_LIBRARY_COVERS_URL}/a/id/{photos[0]}-L.jpg'
            _download_and_attach_image(
                instance=author,
                field_name='photo',
                url=photo_url,
                filename_hint=f"{slugify(author.name)}.jpg",
            )

        if author.biography or author.photo:
            author.save()

    except Exception as e:
        logger.warning(f"OpenLibrary author enrichment skipped for {author.name}: {e}")


def _attach_best_cover(book: Book, info: dict, isbn: str | None):
    """
    Obtiene la mejor carátula disponible desde Google Books u OpenLibrary.
    """
    # 1. Intentar con imageLinks de Google Books (forzando HTTPS)
    image_links = info.get('imageLinks') or {}
    for key in ('extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail'):
        url = image_links.get(key)
        if url:
            if _download_and_attach_image(
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
            if _download_and_attach_image(
                instance=book,
                field_name='cover',
                url=ol_url,
                filename_hint=f"{slugify(book.title)}-{book.id}{size}.jpg",
            ):
                return


def ensure_book_cover(book: Book):
    if book.cover:
        return

    if book.isbn:
        for size in ('-L', '-M'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{book.isbn}{size}.jpg'
            if _download_and_attach_image(book, 'cover', ol_url, f"{slugify(book.title)}-{book.id}{size}.jpg"):
                return

    try:
        query = f'isbn:{book.isbn}' if book.isbn else book.title
        params = {'q': query, 'maxResults': 1, 'printType': 'books'}
        api_key = _get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=7, headers=DEFAULT_HEADERS)
        if resp.ok:
            items = resp.json().get('items') or []
            if items:
                _attach_best_cover(book, items[0].get('volumeInfo', {}), book.isbn)
    except Exception as e:
        logger.warning(f"Error asegurando portada: {e}")


def enrich_book_metadata(book: Book):
    if book.description and book.published_date:
        return

    try:
        query = f'isbn:{book.isbn}' if book.isbn else book.title
        params = {'q': query, 'maxResults': 1, 'printType': 'books'}
        api_key = _get_google_books_api_key()
        if api_key:
            params['key'] = api_key

        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=7, headers=DEFAULT_HEADERS)
        if resp.ok:
            items = resp.json().get('items') or []
            if items:
                info = items[0].get('volumeInfo', {})
                changed = False
                if not book.description and info.get('description'):
                    book.description = info.get('description')
                    changed = True
                if not book.published_date and info.get('publishedDate'):
                    for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                        try:
                            dt = datetime.strptime(info.get('publishedDate'), fmt)
                            book.published_date = dt.date()
                            changed = True
                            break
                        except ValueError:
                            continue
                if changed:
                    book.save()
    except Exception as e:
        logger.warning(f"Error enriqueciendo metadatos del libro: {e}")


def maybe_enrich_book(book: Book):
    """
    Enriquece portada y metadatos del libro (descripción, fecha) de forma exhaustiva.
    """
    ensure_book_cover(book)
    enrich_book_metadata(book)
    book.enrichment_attempted = True
    book.save(update_fields=['enrichment_attempted'])



def _import_books_by_author_from_wikipedia(author: Author) -> int:
    """
    Busca obras notables y novelas del autor en Wikipedia cuando Google Books agota cuota o falla.
    """
    author_name = author.name.strip()
    count = 0
    try:
        sr_params = {
            'action': 'query',
            'list': 'search',
            'srsearch': f'"{author_name}" novela OR libro',
            'format': 'json',
            'srlimit': 8,
        }
        res = requests.get('https://es.wikipedia.org/w/api.php', params=sr_params, timeout=7, headers=DEFAULT_HEADERS)
        if res.ok:
            items = res.json().get('query', {}).get('search', [])
            for item in items:
                page_title = item.get('title', '')
                if not page_title:
                    continue
                # Si el título coincide con el nombre del autor, es su biografía, no un libro
                if page_title.strip().casefold() == author_name.casefold():
                    continue

                clean_title = re.sub(r'\s*\([^)]+\)$', '', page_title).strip()
                existing = Book.objects.filter(title__iexact=clean_title, author=author).first()
                if existing:
                    continue

                sum_url = WIKIPEDIA_API_URL.format(lang='es') + requests.utils.quote(page_title)
                sum_res = requests.get(sum_url, timeout=7, headers=DEFAULT_HEADERS)
                if sum_res.ok:
                    data = sum_res.json()
                    desc = data.get('description', '').lower()
                    if any(term in desc for term in ['desambiguación', 'escritor', 'biografía', 'persona']):
                        continue

                    synopsis = data.get('extract')
                    new_book = Book.objects.create(
                        title=clean_title,
                        author=author,
                        description=synopsis[:2000] if synopsis else None,
                    )
                    count += 1

                    img_info = data.get('originalimage') or data.get('thumbnail') or {}
                    img_url = img_info.get('source')
                    if img_url:
                        _download_and_attach_image(
                            instance=new_book,
                            field_name='cover',
                            url=img_url,
                            filename_hint=f"{slugify(clean_title)}-{new_book.id}.jpg"
                        )
    except Exception as e:
        logger.warning(f"Error en fallback Wikipedia para libros de {author_name}: {e}")
    return count


def import_books_by_author(author_name: str) -> int:
    clean_name = author_name.strip()
    author, _ = Author.objects.get_or_create(name=clean_name)
    maybe_enrich_author(author)
    count = 0

    # 1. Intentar Google Books con inauthor entrecomillado
    try:
        params = {'q': f'inauthor:"{clean_name}"', 'maxResults': 10, 'printType': 'books'}
        api_key = _get_google_books_api_key()
        if api_key:
            params['key'] = api_key

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

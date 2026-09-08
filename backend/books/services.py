import logging
import requests
from datetime import datetime
from django.core.files.base import ContentFile
from django.utils.text import slugify
import unicodedata

from .models import Author, Book

# Constants for external APIs
GOOGLE_BOOKS_API_URL = 'https://www.googleapis.com/books/v1/volumes'
OPEN_LIBRARY_SEARCH_URL = 'https://openlibrary.org/search.json'
OPEN_LIBRARY_AUTHORS_URL = 'https://openlibrary.org/search/authors.json'
OPEN_LIBRARY_COVERS_URL = 'https://covers.openlibrary.org'
WIKIPEDIA_API_URL = 'https://{lang}.wikipedia.org/api/rest_v1/page/summary/'
WIKIPEDIA_OPENSEARCH_URL = 'https://{lang}.wikipedia.org/w/api.php'
WIKIDATA_SEARCH_URL = 'https://www.wikidata.org/w/api.php'
WIKIDATA_ENTITY_URL = 'https://www.wikidata.org/wiki/Special:EntityData/{entity}.json'

logger = logging.getLogger(__name__)

def import_single_by_query(query_isbn: str):
    params = {'q': f'isbn:{query_isbn}', 'maxResults': 1, 'printType': 'books'}
    resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get('items') or []
    if not items:
        return None
    return _create_or_get_from_volume(items[0])

def import_multiple_by_title(title: str, offset: int = 0):
    params = {'q': f'intitle:{title}', 'maxResults': 5, 'startIndex': offset, 'printType': 'books'}
    resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get('items') or []
    books = []
    for volume in items:
        book = _create_or_get_from_volume(volume)
        if book:
            books.append(book)
    if not books:
        books = _import_from_openlibrary_by_title(title, offset=offset)
    return books

def _import_from_openlibrary_by_title(title: str, offset: int = 0):
    try:
        res = requests.get(
            OPEN_LIBRARY_SEARCH_URL,
            params={'title': title, 'offset': offset},
            timeout=10,
            headers={'User-Agent': 'MyBookConnect/1.0'}
        )
        res.raise_for_status()
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
                maybe_enrich_author_from_openlibrary(author_obj)

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
            if cover_id:
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
        logging.exception(e)
        return []

def _create_or_get_from_volume(volume):
    info = volume.get('volumeInfo', {})
    isbn = None
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
        maybe_enrich_author_from_openlibrary(author_obj)

    book = Book(
        title=info.get('title') or 'Desconocido',
        author=author_obj,
        isbn=isbn,
        description=info.get('description')
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
    Descarga una imagen desde una URL y la adjunta al campo especificado del modelo.
    """
    try:
        logger.info(f"Descargando imagen desde: {url}")
        headers = {'User-Agent': 'MyBookConnect/1.0 (contact@example.com)'}
        r = requests.get(url, timeout=10, headers=headers)
        r.raise_for_status()

        content_type = r.headers.get('Content-Type', '')
        if content_type and not content_type.startswith('image/'):
            logger.warning(f"URL no devolvió una imagen válida. Content-Type: {content_type}")
            return False

        content = r.content
        if len(content) < 100:
            logger.warning(f"Imagen descargada es muy pequeña ({len(content)} bytes), ignorando")
            return False

        getattr(instance, field_name).save(filename_hint, ContentFile(content), save=True)
        logger.info(f"Imagen guardada exitosamente: {filename_hint}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de red al descargar imagen desde {url}: {e}")
    except Exception as e:
        logger.exception(f"Error inesperado al descargar imagen desde {url}: {e}")
    return False

def maybe_enrich_author_from_openlibrary(author: Author):
    """
    Enriquece la información del autor desde OpenLibrary.
    Busca biografía y foto del autor.
    """
    if author.biography and author.photo:
        logger.info(f"Autor {author.name} ya tiene biografía y foto, omitiendo OpenLibrary")
        return
    try:
        logger.info(f"Buscando {author.name} en OpenLibrary...")
        rs = requests.get(
            OPEN_LIBRARY_AUTHORS_URL,
            params={'q': author.name},
            timeout=15,
            headers={'User-Agent': 'MyBookConnect/1.0'},
        )
        rs.raise_for_status()
        data = rs.json()
        docs = data.get('docs') or []
        if not docs:
            logger.warning(f"No se encontró {author.name} en OpenLibrary")
            return


        def _norm(s: str) -> str:
            if not s: return ""
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').casefold().strip()
        
        target = _norm(author.name)
        best = None
        
        # Try to find an exact match first
        for d in docs:
            nm = d.get('name')
            if nm and _norm(nm) == target:
                best = d
                break
        
        # If no exact match, try alternate names
        if not best:
            for d in docs:
                alts = d.get('alternate_names') or []
                if any(_norm(alt) == target for alt in alts):
                    best = d
                    break

        if not best and docs:
            first_name = _norm(docs[0].get('name', ''))
            if target in first_name or first_name in target:
                best = docs[0]

        if not best:
            return

        olid = best.get('key')
        logger.info(f"Encontrado autor en OpenLibrary con ID: {olid}")

        # Obtener biografía
        if olid and not author.biography:
            detail_url = f'https://openlibrary.org/authors/{olid.split("/")[-1]}.json'
            rd = requests.get(detail_url, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
            if rd.ok:
                detail = rd.json()
                bio = detail.get('bio')
                if isinstance(bio, dict):
                    bio = bio.get('value')
                if bio:
                    author.biography = bio
                    logger.info(f"Biografía obtenida de OpenLibrary para {author.name}")

        # Obtener foto
        photo_id = None
        photos = best.get('photos') or []
        if photos:
            photo_id = photos[0]
        
        if photo_id and not author.photo:
            photo_url = f'{OPEN_LIBRARY_COVERS_URL}/a/id/{photo_id}-L.jpg'
            logger.info(f"Intentando descargar foto de autor desde: {photo_url}")
            _download_and_attach_image(
                instance=author,
                field_name='photo',
                url=photo_url,
                filename_hint=f"{slugify(author.name)}.jpg"
            )
        
        if author.biography or author.photo:
            author.save()
            logger.info(f"Autor {author.name} guardado con datos de OpenLibrary")
    except Exception as e:
        logger.exception(f"Error enriqueciendo {author.name} desde OpenLibrary: {e}")

    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikidata(author)
    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikipedia(author)

def maybe_enrich_author_from_wikidata(author: Author):
    """
    Enriquece la información del autor desde Wikidata.
    Wikidata suele tener mejores imágenes de autores que otras fuentes.
    """
    if author.biography and author.photo:
        logger.info(f"Autor {author.name} ya tiene biografía y foto, omitiendo Wikidata")
        return
    
    try:
        logger.info(f"Buscando {author.name} en Wikidata...")
        # Buscar entidad en Wikidata
        search_params = {
            'action': 'wbsearchentities',
            'search': author.name,
            'language': 'es',
            'type': 'item',
            'format': 'json',
            'limit': 5
        }

        search_resp = requests.get(WIKIDATA_SEARCH_URL, params=search_params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
        search_resp.raise_for_status()
        search_data = search_resp.json()
        
        results = search_data.get('search', [])
        if not results:
            logger.warning(f"No se encontró {author.name} en Wikidata")
            return
        
        # Buscar el resultado que sea una persona (Q5)
        entity_id = None
        for result in results:
            entity_id = result.get('id')
            # Obtener detalles de la entidad
            entity_url = WIKIDATA_ENTITY_URL.format(entity=entity_id)
            entity_resp = requests.get(entity_url, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
            if entity_resp.ok:
                entity_data = entity_resp.json()
                entities = entity_data.get('entities', {})
                entity_info = entities.get(entity_id, {})
                
                # Verificar si es una persona (P31: instance of -> Q5: human)
                claims = entity_info.get('claims', {})
                instance_of = claims.get('P31', [])
                is_human = any(
                    claim.get('mainsnak', {}).get('datavalue', {}).get('value', {}).get('id') == 'Q5'
                    for claim in instance_of
                )
                
                if is_human:
                    logger.info(f"Encontrada entidad humana en Wikidata: {entity_id}")
                    
                    # Obtener imagen (P18)
                    if not author.photo and 'P18' in claims:
                        image_claims = claims['P18']
                        if image_claims:
                            image_filename = image_claims[0].get('mainsnak', {}).get('datavalue', {}).get('value')
                            if image_filename:
                                # Construir URL de Wikimedia Commons
                                import hashlib
                                md5_hash = hashlib.md5(image_filename.replace(' ', '_').encode('utf-8')).hexdigest()
                                image_url = f"https://upload.wikimedia.org/wikipedia/commons/{md5_hash[0]}/{md5_hash[0:2]}/{image_filename.replace(' ', '_')}"
                                logger.info(f"Intentando descargar foto de Wikidata: {image_url}")
                                _download_and_attach_image(
                                    instance=author,
                                    field_name='photo',
                                    url=image_url,
                                    filename_hint=f"{slugify(author.name)}_wikidata.jpg"
                                )
                    
                    # Obtener descripción en español
                    if not author.biography:
                        descriptions = entity_info.get('descriptions', {})
                        desc_es = descriptions.get('es', {}).get('value')
                        desc_en = descriptions.get('en', {}).get('value')
                        
                        # Preferir descripción en español, sino usar inglés
                        if desc_es:
                            author.biography = desc_es
                            logger.info(f"Descripción en español obtenida de Wikidata para {author.name}")
                        elif desc_en:
                            author.biography = f"[EN] {desc_en}"
                            logger.info(f"Descripción en inglés obtenida de Wikidata para {author.name}")
                    
                    if author.biography or author.photo:
                        author.save()
                        logger.info(f"Autor {author.name} guardado con datos de Wikidata")
                    break
    
    except Exception as e:
        logger.exception(f"Error enriqueciendo {author.name} desde Wikidata: {e}")


def maybe_enrich_author_from_wikipedia(author: Author):
    """
    Enriquece la información del autor desde Wikipedia.
    Prioriza contenido en español, pero obtiene inglés si no hay alternativa.
    """
    if author.biography and author.photo:
        logger.info(f"Autor {author.name} ya tiene biografía y foto, omitiendo Wikipedia")
        return
    
    try:
        logger.info(f"Buscando {author.name} en Wikipedia...")
        name = author.name
        data = None
        found_lang = None
        headers = {'User-Agent': 'MyBookConnect/1.0 (contact@example.com)', 'Accept': 'application/json'}

        for lang in ('es', 'en'):
            logger.info(f"Intentando Wikipedia en {lang}...")
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            try:
                r = requests.get(url, timeout=10, headers=headers)
                if r.ok:
                    temp_data = r.json()
                    if temp_data.get('type') != 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
                        desc = temp_data.get('description', '').lower()
                        if 'disambiguation' not in desc and 'desambiguación' not in desc:
                            data = temp_data
                            found_lang = lang
                            logger.info(f"Encontrado en Wikipedia {lang} (búsqueda directa)")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Wikipedia API request failed for URL {url}: {e}")

            if data:
                break

            sr_url = WIKIPEDIA_OPENSEARCH_URL.format(lang=lang)
            try:
                sr = requests.get(
                    sr_url,
                    params={'action': 'opensearch', 'search': name, 'limit': 3, 'namespace': 0, 'format': 'json'},
                    timeout=10,
                    headers=headers,
                )
                if sr.ok:
                    sdata = sr.json()
                    titles = sdata[1] if isinstance(sdata, list) and len(sdata) > 1 else []
                    for title in titles:
                        if "bibliografía" in title.lower() or "bibliography" in title.lower():
                            continue
                        rr_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(title)
                        rr = requests.get(rr_url, timeout=10, headers=headers)
                        if rr.ok:
                            candidate_data = rr.json()
                            desc = candidate_data.get('description', '').lower()
                            if 'disambiguation' not in desc and 'desambiguación' not in desc:
                                data = candidate_data
                                found_lang = lang
                                logger.info(f"Encontrado en Wikipedia {lang} (opensearch): {title}")
                                break
            except requests.exceptions.RequestException as e:
                logger.warning(f"Wikipedia API request failed for URL {sr_url}: {e}")

            if data:
                break

        if not data:
            logger.warning(f"No se encontró {author.name} en Wikipedia")
            return

        extract = data.get('extract')
        if extract and not author.biography:
            bio_text = extract[:5000]
            if found_lang == 'en':
                bio_text = f"[EN] {bio_text}"
                logger.info(f"Biografía en inglés obtenida de Wikipedia para {author.name}")
            else:
                logger.info(f"Biografía en español obtenida de Wikipedia para {author.name}")
            author.biography = bio_text

        if not author.photo:
            original_img = data.get('originalimage') or {}
            img_url = original_img.get('source')
            if not img_url:
                thumb = data.get('thumbnail') or {}
                img_url = thumb.get('source')
            if img_url:
                logger.info(f"Intentando descargar foto de Wikipedia: {img_url}")
                _download_and_attach_image(
                    instance=author,
                    field_name='photo',
                    url=img_url,
                    filename_hint=f"{slugify(author.name)}_wikipedia.jpg"
                )

        if author.biography or author.photo:
            author.save()
            logger.info(f"Autor {author.name} guardado con datos de Wikipedia")

    except Exception as e:
        logger.exception(f"Error enriqueciendo {author.name} desde Wikipedia: {e}")

def _attach_best_cover(book: Book, info: dict, isbn: str | None):
    if isbn:
        for size in ('-XL', '-L', '-M', '-S'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{isbn}{size}.jpg'
            try:
                head = requests.head(ol_url, timeout=5)
                if head.ok and head.headers.get('Content-Type', '').startswith('image/'):
                    _download_and_attach_image(
                        instance=book,
                        field_name='cover',
                        url=ol_url,
                        filename_hint=f"{slugify(book.title)}-{book.id}{size}.jpg"
                    )
                    return
            except Exception as e:
                logging.exception(e)
                continue
    image_links = info.get('imageLinks') or {}
    for key in ('extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail'):
        url = image_links.get(key)
        if url:
            if _download_and_attach_image(
                instance=book,
                field_name='cover',
                url=url,
                filename_hint=f"{slugify(book.title)}-{book.id}.jpg"
            ):
                return

def ensure_book_cover(book: Book):
    """
    Intenta descargar la portada si no existe.
    """
    if book.cover:
        return

    logging.info(f"Attempting to fetch missing cover for book: {book.title} (ISBN: {book.isbn})")

    # 1. Intentar con OpenLibrary por ISBN si existe
    if book.isbn:
        for size in ('-L', '-M'):
            ol_url = f'{OPEN_LIBRARY_COVERS_URL}/b/isbn/{book.isbn}{size}.jpg'
            if _download_and_attach_image(book, 'cover', ol_url, f"{slugify(book.title)}-{book.id}{size}.jpg"):
                logging.info(f"Cover found on OpenLibrary for {book.title}")
                return

    # 2. Buscar en Google Books para obtener imageLinks
    try:
        query = f'isbn:{book.isbn}' if book.isbn else f'intitle:{book.title}'
        params = {'q': query, 'maxResults': 1, 'printType': 'books'}
        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
        if resp.ok:
            data = resp.json()
            items = data.get('items') or []
            if items:
                volume_info = items[0].get('volumeInfo', {})
                _attach_best_cover(book, volume_info, book.isbn)
    except Exception as e:
        logging.exception(f"Error searching Google Books for cover: {e}")

def enrich_book_metadata(book: Book):
    """
    Intenta completar metadatos faltantes (descripción, fecha) usando Google Books.
    """
    if book.description and book.published_date:
        return

    try:
        query = f'isbn:{book.isbn}' if book.isbn else f'intitle:{book.title}'
        params = {'q': query, 'maxResults': 1, 'printType': 'books'}
        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
        if resp.ok:
            data = resp.json()
            items = data.get('items') or []
            if items:
                info = items[0].get('volumeInfo', {})
                changed = False
                if not book.description and info.get('description'):
                    book.description = info.get('description')
                    changed = True
                
                if not book.published_date:
                    published = info.get('publishedDate')
                    if published:
                        for fmt in ('%Y-%m-%d', '%Y-%m', '%Y'):
                            try:
                                dt = datetime.strptime(published, fmt)
                                book.published_date = dt.date()
                                changed = True
                                break
                            except ValueError:
                                continue
                
                if changed:
                    book.save()
    except Exception as e:
        logging.exception(f"Error enriching book metadata: {e}")

def import_books_by_author(author_name: str):
    """
    Busca libros de un autor en Google Books y los añade a la BD.
    """
    try:
        params = {'q': f'inauthor:{author_name}', 'maxResults': 10, 'printType': 'books', 'langRestrict': 'es'}
        resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
        if resp.ok:
            data = resp.json()
            items = data.get('items') or []
            count = 0
            for volume in items:
                if _create_or_get_from_volume(volume):
                    count += 1
            return count
    except Exception as e:
        logging.exception(f"Error importing books by author {author_name}: {e}")
    return 0


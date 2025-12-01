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

def import_single_by_query(query_isbn: str):
    params = {'q': f'isbn:{query_isbn}', 'maxResults': 1, 'printType': 'books'}
    resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
    resp.raise_for_status()
    payload = resp.json()
    items = payload.get('items') or []
    if not items:
        return None
    return _create_or_get_from_volume(items[0])

def import_multiple_by_title(title: str, offset: int = 0):
    params = {'q': f'intitle:{title}', 'maxResults': 5, 'startIndex': offset, 'printType': 'books'}
    resp = requests.get(GOOGLE_BOOKS_API_URL, params=params, timeout=10)
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
        res = requests.get(OPEN_LIBRARY_SEARCH_URL, params={'title': title, 'offset': offset}, timeout=10)
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
    try:
        headers = {'User-Agent': 'MyBookConnect/1.0 (contact@example.com)'}
        r = requests.get(url, stream=True, timeout=10, headers=headers)
        if r.ok:
            getattr(instance, field_name).save(filename_hint, ContentFile(r.content), save=True)
            return True
    except Exception as e:
        logging.exception(f"Error downloading image from {url}: {e}")
    return False

def maybe_enrich_author_from_openlibrary(author: Author):
    if author.biography and author.photo:
        return
    try:
        rs = requests.get(OPEN_LIBRARY_AUTHORS_URL, params={'q': author.name}, timeout=15, headers={'User-Agent': 'MyBookConnect/1.0'})
        rs.raise_for_status()
        data = rs.json()
        docs = data.get('docs') or []
        if not docs:
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
        
        # Fallback to the first result if it's a very close match (contains the name)
        if not best and docs:
             first_name = _norm(docs[0].get('name', ''))
             if target in first_name or first_name in target:
                 best = docs[0]

        if not best:
            return

        olid = best.get('key')

        if olid:
            detail_url = f'https://openlibrary.org/authors/{olid.split("/")[-1]}.json'
            rd = requests.get(detail_url, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
            if rd.ok:
                detail = rd.json()
                bio = detail.get('bio')
                if isinstance(bio, dict):
                    bio = bio.get('value')
                if bio and not author.biography:
                    author.biography = bio

        photo_id = None
        photos = best.get('photos') or []
        if photos:
            photo_id = photos[0]
        
        if photo_id and not author.photo:
            photo_url = f'{OPEN_LIBRARY_COVERS_URL}/a/id/{photo_id}-L.jpg'
            _download_and_attach_image(
                instance=author,
                field_name='photo',
                url=photo_url,
                filename_hint=f"{slugify(author.name)}.jpg"
            )
        author.save()
    except Exception as e:
        logging.exception(e)
    
    # Always try Wikipedia if bio or photo is missing, even if OpenLibrary failed or succeeded partially
    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikipedia(author)

def maybe_enrich_author_from_wikipedia(author: Author):
    try:
        name = author.name
        data = None
        headers = {'User-Agent': 'MyBookConnect/1.0 (contact@example.com)', 'Accept': 'application/json'}
        # Try multiple languages and search strategies
        for lang in ('es', 'en'):
            # Strategy 1: Direct page access
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            try:
                r = requests.get(url, timeout=10, headers=headers)
                if r.ok:
                    data = r.json()
                    if data.get('type') == 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
                        data = None
                    else:
                        # Check if it's a disambiguation page
                        desc = data.get('description', '').lower()
                        if 'disambiguation' in desc or 'desambiguación' in desc:
                            data = None
            except Exception:
                pass
            except requests.exceptions.RequestException as e:
                logging.warning(f"Wikipedia API request failed for URL {url}: {e}")

            if data: break

            # Strategy 2: OpenSearch (Search for titles)
            sr_url = WIKIPEDIA_OPENSEARCH_URL.format(lang=lang)
            try:
                sr = requests.get(sr_url, params={'action': 'opensearch', 'search': name, 'limit': 3, 'namespace': 0, 'format': 'json'}, timeout=10, headers=headers)
                if sr.ok:
                    sdata = sr.json()
                    # sdata format: [search_term, [titles], [descriptions], [urls]]
                    titles = sdata[1] if isinstance(sdata, list) and len(sdata) > 1 else []
                    
                    for title in titles:
                        # Skip if title seems to be a list of works or unrelated
                        if "bibliografía" in title.lower() or "bibliography" in title.lower():
                            continue
                            
                        rr_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(title)
                        rr = requests.get(rr_url, timeout=10, headers=headers)
                        if rr.ok:
                            candidate_data = rr.json()
                            # Verify it's not a disambiguation page
                            desc = candidate_data.get('description', '').lower()
                            if 'disambiguation' not in desc and 'desambiguación' not in desc:
                                data = candidate_data
                                break
            except Exception:
                pass
            except requests.exceptions.RequestException as e:
                logging.warning(f"Wikipedia API request failed for URL {sr_url}: {e}")
            
            if data: break

        if not data:
            return

        extract = data.get('extract')
        if extract and not author.biography:
            author.biography = extract[:5000]
        
        thumb = data.get('thumbnail') or {}
        thumb_url = thumb.get('source')
        if thumb_url and not author.photo:
            # High res image logic: Wikipedia thumbnails are often small. 
            # Try to get a larger version by modifying the URL if possible, or just use what we have.
            # Typical URL: https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Image.jpg/50px-Image.jpg
            # We can try to remove the /thumb/ part and the suffix to get the original, but it's risky.
            # For now, let's just use the provided URL but maybe request a larger size if the API supported it.
            # The current API call returns what it returns.
            _download_and_attach_image(
                instance=author,
                field_name='photo',
                url=thumb_url,
                filename_hint=f"{slugify(author.name)}.jpg"
            )
        author.save()
    except Exception as e:
        logging.exception(e)

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


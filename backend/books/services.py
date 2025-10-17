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
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        content = r.content
    except Exception as e:
        logging.exception(e)

def maybe_enrich_author_from_openlibrary(author: Author):
    if author.biography and author.photo:
        return
    try:
        rs = requests.get(OPEN_LIBRARY_AUTHORS_URL, params={'q': author.name}, timeout=10)
        rs.raise_for_status()
        data = rs.json()
        docs = data.get('docs') or []
        if not docs:
            return
        def _norm(s: str) -> str:
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').casefold().strip()
        target = _norm(author.name)
        best = None
        for d in docs:
            nm = d.get('name') or d.get('alternate_names', [None])[0]
            if not nm:
                continue
            if _norm(nm) == target:
                best = d
                break
        if not best:
            best = docs[0]
        olid = best.get('key')

        if olid:
            detail_url = f'https://openlibrary.org/authors/{olid.split("/")[-1]}.json'
            rd = requests.get(detail_url, timeout=10)
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
    if not author.biography or not author.photo:
        maybe_enrich_author_from_wikipedia(author)

def maybe_enrich_author_from_wikipedia(author: Author):
    try:
        name = author.name
        data = None
        for lang in ('es', 'en'):
            url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(name)
            r = requests.get(url, timeout=8, headers={'Accept': 'application/json'})
            if r.ok:
                data = r.json()
                if data.get('type') != 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
                    break
                else:
                    data = None
            if data is None:
                sr_url = WIKIPEDIA_OPENSEARCH_URL.format(lang=lang)
                sr = requests.get(sr_url, params={'action': 'opensearch', 'search': name, 'limit': 1, 'namespace': 0, 'format': 'json'}, timeout=8)
                if sr.ok:
                    sdata = sr.json()
                    titles = sdata[1] if isinstance(sdata, list) and len(sdata) > 1 else []
                    if titles:
                        title = titles[0]
                        rr_url = WIKIPEDIA_API_URL.format(lang=lang) + requests.utils.quote(title)
                        rr = requests.get(rr_url, timeout=8, headers={'Accept': 'application/json'})
                        if rr.ok:
                            data = rr.json()
                            break
        if not data:
            return
        extract = data.get('extract')
        if extract and not author.biography:
            author.biography = extract[:5000]
        thumb = data.get('thumbnail') or {}
        thumb_url = thumb.get('source')
        if thumb_url and not author.photo:
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
            _download_and_attach_image(
                instance=book,
                field_name='cover',
                url=url,
                filename_hint=f"{slugify(book.title)}-{book.id}.jpg"
            )
            return

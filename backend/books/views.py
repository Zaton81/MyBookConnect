from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.core.files.base import ContentFile
from django.utils.text import slugify
import requests
from datetime import datetime
from .models import Author, Book, Review, UserBook
from .serializers import AuthorSerializer, BookSerializer, ReviewSerializer, UserBookSerializer
import unicodedata


class BookListCreateView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        queryset = Book.objects.all()
        q = self.request.query_params.get('q')
        if q:
            # Búsqueda simple por título o ISBN
            return queryset.filter(Q(title__icontains=q) | Q(isbn__icontains=q))
        return queryset

    def perform_create(self, serializer):
        serializer.save()


class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AuthorDetailView(generics.RetrieveAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        instance: Author = self.get_object()
        # Enriquecer en lectura si faltan datos
        if not instance.biography or not instance.photo:
            try:
                ImportBookView()._maybe_enrich_author_from_openlibrary(instance)
                if not instance.biography or not instance.photo:
                    ImportBookView()._maybe_enrich_author_from_wikipedia(instance)
            except Exception as e:
                print(f"Error enriching author {instance.name}: {e}")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class BookDetailView(generics.RetrieveAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticated,)


class UserBookPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'


class UserBookListCreateView(generics.ListCreateAPIView):
    serializer_class = UserBookSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = UserBookPagination

    def get_queryset(self):
        queryset = UserBook.objects.filter(user=self.request.user).select_related('book')
        params = self.request.query_params
        # Filtros booleanos
        def parse_bool(value):
            if value is None or value == '':
                return None
            return value.lower() in ('1', 'true', 'yes', 'si', 'sí')

        is_read = parse_bool(params.get('is_read'))
        wishlist = parse_bool(params.get('wishlist'))
        is_digital = parse_bool(params.get('is_digital'))
        owned = parse_bool(params.get('owned'))
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read)
        if wishlist is not None:
            queryset = queryset.filter(wishlist=wishlist)
        if is_digital is not None:
            queryset = queryset.filter(is_digital=is_digital)
        if owned is not None:
            queryset = queryset.filter(owned=owned)

        # Nota mínima
        min_rating = params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=int(min_rating))
            except ValueError:
                pass

        # Búsqueda por título
        search = params.get('search') or params.get('q')
        if search:
            queryset = queryset.filter(book__title__icontains=search)

        # Ordenación
        ordering = params.get('ordering')
        allowed = {
            'updated_at', '-updated_at',
            'rating', '-rating',
            'book__title', '-book__title',
            'wishlist', '-wishlist',
            'is_digital', '-is_digital',
            'owned', '-owned',
        }
        if ordering in allowed:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-updated_at')

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserBookDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserBookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return get_object_or_404(UserBook, pk=self.kwargs['pk'], user=self.request.user)


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        book_id = self.request.query_params.get('book')
        if book_id:
            return Review.objects.filter(book_id=book_id)
        return Review.objects.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ImportBookView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        query_isbn = (request.data.get('isbn') or '').strip()
        query_title = (request.data.get('title') or request.data.get('q') or '').strip()
        offset = request.data.get('offset', 0)

        if not query_isbn and not query_title:
            return Response({'detail': 'Proporcione isbn o title'}, status=400)

        try:
            if query_isbn:
                book = self._import_single_by_query(query_isbn=query_isbn)
                if not book:
                    return Response({'detail': 'No se encontraron resultados'}, status=404)
                return Response(BookSerializer(book).data, status=201)
            # título: crear múltiples candidatos
            books = self._import_multiple_by_title(query_title, offset=offset)
            if not books:
                return Response({'detail': 'No se encontraron resultados'}, status=404)
            return Response(BookSerializer(books, many=True).data, status=201)
        except Exception as exc:
            return Response({'detail': f'Error importando libro: {exc}'}, status=500)

    def _import_single_by_query(self, query_isbn: str):
        url = 'https://www.googleapis.com/books/v1/volumes'
        params = {'q': f'isbn:{query_isbn}', 'maxResults': 1, 'printType': 'books'}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get('items') or []
        if not items:
            return None
        return self._create_or_get_from_volume(items[0])

    def _import_multiple_by_title(self, title: str, offset: int = 0):
        url = 'https://www.googleapis.com/books/v1/volumes'
        params = {'q': f'intitle:{title}', 'maxResults': 5, 'startIndex': offset, 'printType': 'books'}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get('items') or []
        books = []
        for volume in items:
            book = self._create_or_get_from_volume(volume)
            if book:
                books.append(book)
        # Fallback: Open Library search por título si no hubo resultados o para complementar
        if not books:
            books = self._import_from_openlibrary_by_title(title, offset=offset)
        return books

    def _import_from_openlibrary_by_title(self, title: str, offset: int = 0):
        try:
            # https://openlibrary.org/search.json?title=...
            res = requests.get('https://openlibrary.org/search.json', params={'title': title, 'offset': offset}, timeout=10)
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
                    self._maybe_enrich_author_from_openlibrary(author_obj)

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
                # Portada por cover_id si existe
                if cover_id:
                    ol_cover_url = f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg'
                    self._download_and_attach_image(
                        instance=book,
                        field_name='cover',
                        url=ol_cover_url,
                        filename_hint=f"{slugify(book.title)}-{book.id}.jpg"
                    )
                results.append(book)
            return results
        except Exception:
            return []

    def _create_or_get_from_volume(self, volume):
        info = volume.get('volumeInfo', {})
        # ISBN
        isbn = None
        for ident in info.get('industryIdentifiers', []) or []:
            if ident.get('type') in ('ISBN_13', 'ISBN_10'):
                isbn = ident.get('identifier')
                break
        if isbn:
            existing = Book.objects.filter(isbn=isbn).first()
            if existing:
                return existing

        # Autor
        author_obj = None
        authors_list = info.get('authors') or []
        if authors_list:
            author_name = authors_list[0]
            author_obj, _ = Author.objects.get_or_create(name=author_name)
            self._maybe_enrich_author_from_openlibrary(author_obj)

        # Crear libro
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
        # Mejor selección de portada
        self._attach_best_cover(book=book, info=info, isbn=isbn)
        return book

    def _download_and_attach_image(self, instance, field_name: str, url: str, filename_hint: str):
        try:
            r = requests.get(url, timeout=10)
            r.raise_for_status()
            content = r.content
            getattr(instance, field_name).save(filename_hint, ContentFile(content), save=True)
        except Exception:
            # Silencioso: si falla la imagen, no bloquear importación
            pass

    def _maybe_enrich_author_from_openlibrary(self, author: Author):
        if author.biography and author.photo:
            return
        try:
            # 1) Buscar autor por nombre
            search_url = 'https://openlibrary.org/search/authors.json'
            rs = requests.get(search_url, params={'q': author.name}, timeout=10)
            rs.raise_for_status()
            data = rs.json()
            docs = data.get('docs') or []
            if not docs:
                return
            def _norm(s: str) -> str:
                return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').casefold().strip()
            target = _norm(author.name)
            best = None
            # Preferir coincidencia exacta por nombre normalizado
            for d in docs:
                nm = d.get('name') or d.get('alternate_names', [None])[0]
                if not nm:
                    continue
                if _norm(nm) == target:
                    best = d
                    break
            if not best:
                best = docs[0]
            olid = best.get('key')  # "/authors/OL12345A"

            # 2) Obtener detalle del autor
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

            # 3) Foto del autor (ID de foto principal)
            photo_id = None
            photos = best.get('photos') or []
            if photos:
                photo_id = photos[0]
            if photo_id and not author.photo:
                photo_url = f'https://covers.openlibrary.org/a/id/{photo_id}-L.jpg'
                self._download_and_attach_image(
                    instance=author,
                    field_name='photo',
                    url=photo_url,
                    filename_hint=f"{slugify(author.name)}.jpg"
                )
            author.save()
        except Exception as e:
            print(f"Error enriching author from OpenLibrary: {e}")
        # Si aún falta bio o foto, intentar Wikipedia en español
        if not author.biography or not author.photo:
            self._maybe_enrich_author_from_wikipedia(author)

    def _maybe_enrich_author_from_wikipedia(self, author: Author):
        try:
            name = author.name
            # 1) Intento directo en ES summary
            data = None
            for lang in ('es', 'en'):
                url = f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(name)}'
                r = requests.get(url, timeout=8, headers={'Accept': 'application/json'})
                if r.ok:
                    data = r.json()
                    if data.get('type') != 'https://mediawiki.org/wiki/HyperSwitch/errors/not_found':
                        break
                    else:
                        data = None
                # Si no ok o not_found, probar opensearch para encontrar el título correcto
                if data is None:
                    sr = requests.get(
                        f'https://{lang}.wikipedia.org/w/api.php',
                        params={
                            'action': 'opensearch', 'search': name, 'limit': 1, 'namespace': 0, 'format': 'json'
                        }, timeout=8
                    )
                    if sr.ok:
                        sdata = sr.json()
                        titles = sdata[1] if isinstance(sdata, list) and len(sdata) > 1 else []
                        if titles:
                            title = titles[0]
                            rr = requests.get(
                                f'https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}',
                                timeout=8, headers={'Accept': 'application/json'}
                            )
                            if rr.ok:
                                data = rr.json()
                                break
            if not data:
                return
            # Bio
            extract = data.get('extract')
            if extract and not author.biography:
                # Limitar longitud para evitar textos excesivos
                author.biography = extract[:5000]
            # Foto
            thumb = data.get('thumbnail') or {}
            thumb_url = thumb.get('source')
            if thumb_url and not author.photo:
                self._download_and_attach_image(
                    instance=author,
                    field_name='photo',
                    url=thumb_url,
                    filename_hint=f"{slugify(author.name)}.jpg"
                )
            author.save()
        except Exception as e:
            print(f"Error enriching author from Wikipedia: {e}")

    def _attach_best_cover(self, book: Book, info: dict, isbn: str | None):
        # 1) Probar Open Library por ISBN con tamaños grandes (XL, L)
        if isbn:
            for size in ('-XL', '-L', '-M', '-S'):
                ol_url = f'https://covers.openlibrary.org/b/isbn/{isbn}{size}.jpg'
                try:
                    head = requests.head(ol_url, timeout=5)
                    if head.ok and head.headers.get('Content-Type', '').startswith('image/'):
                        self._download_and_attach_image(
                            instance=book,
                            field_name='cover',
                            url=ol_url,
                            filename_hint=f"{slugify(book.title)}-{book.id}{size}.jpg"
                        )
                        return
                except Exception:
                    continue
        # 2) Fallback a Google con los tamaños más grandes disponibles
        image_links = info.get('imageLinks') or {}
        for key in ('extraLarge', 'large', 'medium', 'small', 'thumbnail', 'smallThumbnail'):
            url = image_links.get(key)
            if url:
                self._download_and_attach_image(
                    instance=book,
                    field_name='cover',
                    url=url,
                    filename_hint=f"{slugify(book.title)}-{book.id}.jpg"
                )
                return
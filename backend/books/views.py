import logging
from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import Author, Book, Review, UserBook, Errata, ErrataStatus
from .serializers import AuthorSerializer, BookSerializer, ReviewSerializer, UserBookSerializer, ErrataSerializer
from . import services


class BookListCreateView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        queryset = Book.objects.select_related('author')
        q = self.request.query_params.get('q')
        if q:
            return queryset.filter(Q(title__icontains=q) | Q(isbn__icontains=q))
        return queryset

    def perform_create(self, serializer):
        serializer.save()


class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AuthorDetailView(generics.RetrieveAPIView):
    queryset = Author.objects.all().prefetch_related('books')
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        instance: Author = self.get_object()
        # Solo intentar enriquecer si no se ha intentado antes
        if not instance.enrichment_attempted:
            try:
                # Intentar OpenLibrary primero
                services.maybe_enrich_author_from_openlibrary(instance)
                # Las llamadas a Wikidata y Wikipedia ya están incluidas en la función anterior
                # pero si OpenLibrary no llamó a las otras, forzamos aquí
                if not instance.biography or not instance.photo:
                    services.maybe_enrich_author_from_wikidata(instance)
                if not instance.biography or not instance.photo:
                    services.maybe_enrich_author_from_wikipedia(instance)
                # Marcar como intentado independientemente del resultado
                instance.enrichment_attempted = True
                instance.save(update_fields=['enrichment_attempted'])
            except Exception as e:
                logging.exception(e)
                # Marcar como intentado incluso si hubo error
                instance.enrichment_attempted = True
                instance.save(update_fields=['enrichment_attempted'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class AuthorBooksView(APIView):
    """Listar todos los libros de un autor guardados localmente."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk):
        books = Book.objects.filter(author_id=pk).select_related('author')
        local = BookSerializer(books, many=True).data

        # Búsqueda externa opcional cuando hay pocos locales
        external = []
        try:
            author = Author.objects.get(pk=pk)
            # Buscar en Google Books por autor
            import requests
            params = {'q': f'inauthor:"{author.name}"', 'maxResults': 5}
            gb = requests.get(services.GOOGLE_BOOKS_API_URL, params=params, timeout=10, headers={'User-Agent': 'MyBookConnect/1.0'})
            if gb.ok:
                data = gb.json()
                items = data.get('items') or []
                for v in items:
                    info = v.get('volumeInfo', {})
                    external.append({
                        'id': v.get('id'),
                        'title': info.get('title'),
                        'cover': (info.get('imageLinks') or {}).get('thumbnail'),
                        'published_date': info.get('publishedDate')
                    })
        except Exception as e:
            logging.exception(e)

        return Response({'local': local, 'external': external})


class BookDetailView(generics.RetrieveAPIView):
    queryset = Book.objects.select_related('author')
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.enrichment_attempted:
            instance.enrichment_attempted = True
            try:
                if not instance.cover:
                    services.ensure_book_cover(instance)
                if not instance.description or not instance.published_date:
                    services.enrich_book_metadata(instance)
                instance.save(update_fields=['enrichment_attempted'])
                instance.refresh_from_db()
            except Exception as e:
                logging.exception(f"Error enriching book in detail view: {e}")
                instance.save(update_fields=['enrichment_attempted'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class UserBookPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    page_query_param = 'page'


class UserBookListCreateView(generics.ListCreateAPIView):
    serializer_class = UserBookSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = UserBookPagination

    def get_queryset(self):
        queryset = UserBook.objects.filter(user=self.request.user).select_related('book', 'book__author')
        params = self.request.query_params

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

        min_rating = params.get('min_rating')
        if min_rating:
            try:
                queryset = queryset.filter(rating__gte=int(min_rating))
            except ValueError:
                pass

        search = params.get('search') or params.get('q')
        if search:
            queryset = queryset.filter(book__title__icontains=search)

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


class UserBookByBookView(APIView):
    """Endpoint optimizado para obtener el UserBook de un libro específico"""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, book_id):
        try:
            user_book = UserBook.objects.select_related('book', 'book__author').get(
                user=request.user,
                book_id=book_id
            )
            serializer = UserBookSerializer(user_book)
            return Response(serializer.data)
        except UserBook.DoesNotExist:
            return Response({'detail': 'No encontrado'}, status=404)


class ReviewListCreateView(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        from django.db.models import Exists, OuterRef
        queryset = Review.objects.all()
        
        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)
            
        user = self.request.user
        if user.is_authenticated:
            following_subquery = user.following.filter(pk=OuterRef('user_id'))
            queryset = queryset.annotate(is_friend=Exists(following_subquery))
            
        return queryset

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
                book = services.import_single_by_query(query_isbn=query_isbn)
                if not book:
                    return Response({'detail': 'No se encontraron resultados'}, status=404)
                return Response(BookSerializer(book).data, status=201)
            
            books = services.import_multiple_by_title(query_title, offset=offset)
            if not books:
                return Response({'detail': 'No se encontraron resultados'}, status=404)
            return Response(BookSerializer(books, many=True).data, status=201)
        except Exception as exc:
            logging.exception(exc)
            return Response({'detail': 'Ocurrió un error al importar el libro.'}, status=500)


class RecommendationView(generics.ListAPIView):
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        book_id = self.kwargs.get('pk')
        try:
            book = Book.objects.get(pk=book_id)
        except Book.DoesNotExist:
            return Book.objects.none()

        categories = book.categories.all()
        if not categories:
            return Book.objects.filter(author=book.author).exclude(id=book.id).order_by('-average_rating')[:5]

        user_books = UserBook.objects.filter(user=self.request.user).values_list('book_id', flat=True)

        return Book.objects.filter(categories__in=categories) \
            .exclude(id=book.id) \
            .exclude(id__in=user_books) \
            .distinct() \
            .order_by('-average_rating')[:5]


class AuthorBookRefreshView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, pk):
        try:
            author = Author.objects.get(pk=pk)
            count = services.import_books_by_author(author.name)
            return Response({'count': count, 'detail': f'Se encontraron {count} libros nuevos.'})
        except Author.DoesNotExist:
            return Response({'detail': 'Autor no encontrado'}, status=404)
        except Exception as e:
            logging.exception(e)
            return Response({'detail': 'Error al actualizar libros'}, status=500)


class ErrataListCreateView(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ErrataSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'is_editor', False) or user.is_staff or user.is_superuser:
            return Errata.objects.select_related('book', 'author', 'user', 'editor')
        return Errata.objects.filter(user=user).select_related('book', 'author', 'user', 'editor')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ErrataDetailUpdateView(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ErrataSerializer
    queryset = Errata.objects.select_related('book', 'author', 'user', 'editor')

    def update(self, request, *args, **kwargs):
        instance: Errata = self.get_object()
        user = request.user
        partial = kwargs.pop('partial', True)
        data = request.data.copy()
        if not (getattr(user, 'is_editor', False) or user.is_staff or user.is_superuser):
            if instance.user_id != user.id:
                return Response({'detail': 'No autorizado'}, status=403)
            allowed_user = {'text'}
            data = {k: v for k, v in data.items() if k in allowed_user}
            serializer = self.get_serializer(instance, data=data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

        allowed_editor = {'status', 'resolution_notes'}
        data = {k: v for k, v in data.items() if k in allowed_editor}
        if 'status' in data and data['status'] not in ErrataStatus.values:
            return Response({'detail': 'Estado inválido'}, status=400)
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(editor=user)
        return Response(serializer.data)


class SocialFeedView(APIView):
    """
    Feed de actividad social comunitaria en tiempo real: últimas lecturas y reseñas.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        reviews = Review.objects.select_related('user', 'book', 'book__author').order_by('-created_at')[:15]
        user_books = UserBook.objects.filter(is_read=True).select_related('user', 'book', 'book__author').order_by('-updated_at')[:15]

        items = []
        for r in reviews:
            items.append({
                'id': f'review_{r.id}',
                'type': 'review',
                'timestamp': r.created_at.isoformat(),
                'user': {
                    'id': r.user.id,
                    'username': r.user.username,
                    'avatar': r.user.avatar.url if r.user.avatar else None,
                },
                'book': {
                    'id': r.book.id,
                    'title': r.book.title,
                    'cover': r.book.cover.url if r.book.cover else None,
                    'author_name': r.book.author.name if r.book.author else '',
                },
                'rating': r.rating,
                'comment': r.text,
            })

        for ub in user_books:
            items.append({
                'id': f'reading_{ub.id}',
                'type': 'finished_reading',
                'timestamp': ub.updated_at.isoformat(),
                'user': {
                    'id': ub.user.id,
                    'username': ub.user.username,
                    'avatar': ub.user.avatar.url if ub.user.avatar else None,
                },
                'book': {
                    'id': ub.book.id,
                    'title': ub.book.title,
                    'cover': ub.book.cover.url if ub.book.cover else None,
                    'author_name': ub.book.author.name if ub.book.author else '',
                },
                'rating': ub.rating,
            })

        items.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response({'results': items[:20]})


class TrendingBooksView(APIView):
    """
    Libros más populares y leídos en la plataforma.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from django.db.models import Count
        trending = Book.objects.annotate(
            readers_count=Count('user_entries', distinct=True),
            reviews_count=Count('reviews', distinct=True)
        ).select_related('author').order_by('-readers_count', '-average_rating', '-created_at')[:12]

        results = []
        for b in trending:
            results.append({
                'id': b.id,
                'title': b.title,
                'cover': b.cover.url if b.cover else None,
                'author_name': b.author.name if b.author else '',
                'average_rating': b.average_rating,
                'readers_count': b.readers_count,
                'reviews_count': b.reviews_count,
            })
        return Response({'results': results})


class ReadingMatchView(APIView):
    """
    Calcula el porcentaje de afinidad literaria y libros compartidos entre usuarios.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        UserModel = get_user_model()
        target_user = get_object_or_404(UserModel, id=user_id)

        if target_user == request.user:
            return Response({'match_percentage': 100, 'is_self': True, 'common_books': []})

        my_books = set(UserBook.objects.filter(user=request.user, is_read=True).values_list('book_id', flat=True))
        their_books = set(UserBook.objects.filter(user=target_user, is_read=True).values_list('book_id', flat=True))

        common_ids = my_books.intersection(their_books)
        total_unique = len(my_books.union(their_books))

        if total_unique == 0:
            match_percentage = 50
        else:
            match_percentage = min(100, int((len(common_ids) / total_unique) * 100) + 40)

        common_books = Book.objects.filter(id__in=common_ids).select_related('author')[:5]
        common_serialized = [{
            'id': b.id,
            'title': b.title,
            'cover': b.cover.url if b.cover else None,
            'author_name': b.author.name if b.author else '',
        } for b in common_books]

        return Response({
            'match_percentage': match_percentage,
            'common_books_count': len(common_ids),
            'common_books': common_serialized,
            'my_read_count': len(my_books),
            'their_read_count': len(their_books),
        })


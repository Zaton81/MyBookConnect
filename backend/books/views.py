import logging
from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import Author, Book, Review, UserBook
from .serializers import AuthorSerializer, BookSerializer, ReviewSerializer, UserBookSerializer
from . import services


class BookListCreateView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        queryset = Book.objects.all()
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
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def retrieve(self, request, *args, **kwargs):
        instance: Author = self.get_object()
        if not instance.biography or not instance.photo:
            try:
                services.maybe_enrich_author_from_openlibrary(instance)
                if not instance.biography or not instance.photo:
                    services.maybe_enrich_author_from_wikipedia(instance)
            except Exception as e:
                logging.exception(e)
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

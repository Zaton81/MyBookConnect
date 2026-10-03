import logging

from django.contrib.auth import get_user_model
from django.db.models import Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books.models import Author, Book, normalize_isbn, normalize_title
from books.serializers import AuthorSerializer, BookSerializer
from users.privacy_service import PrivacyService
from users.serializers import UserBasicSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class GlobalSearchView(APIView):
    """
    Búsqueda global unificada (RoadmapV3 Sección 9.3).
    Permite consultar en una única llamada libros, autores y lectores comunitarios,
    respetando la deduplicación de ediciones (múltiples ISBNs) y las políticas de privacidad.
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Búsqueda global unificada (libros, autores, usuarios)",
        description=(
            "Devuelve resultados categorizados en 'books', 'authors' y 'users'. "
            "Resuelve libros por título, autor, sinopsis o cualquiera de sus ISBNs "
            "(físicos o digitales unificados), autores por nombre y alias, "
            "y usuarios públicos respetando bloqueos mutuos y privacidad RGPD."
        ),
        parameters=[
            OpenApiParameter(
                name='q',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Término de búsqueda general (título, autor, ISBN o nombre de usuario).",
            ),
            OpenApiParameter(
                name='type',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                default='all',
                description="Filtrar por entidad específica: 'all', 'books', 'authors', 'users'.",
            ),
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                default=10,
                description="Cantidad máxima de resultados por categoría (1 a 50).",
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        q = (request.query_params.get('q') or '').strip()
        type_filter = (request.query_params.get('type') or 'all').strip().lower()
        try:
            limit = max(1, min(int(request.query_params.get('limit', 10)), 50))
        except (ValueError, TypeError):
            limit = 10

        if not q:
            return Response({
                'query': '',
                'type': type_filter,
                'total_results': 0,
                'books': [],
                'authors': [],
                'users': [],
            })

        books_data = []
        authors_data = []
        users_data = []

        # 1. Búsqueda de Libros
        if type_filter in ('all', 'books'):
            books_set = {}
            # a) Búsqueda por ISBN exacto o alternativo (físico/digital unificado)
            clean_isbn = normalize_isbn(q)
            if clean_isbn:
                matched_book = Book.find_by_isbn(clean_isbn)
                if matched_book:
                    books_set[matched_book.id] = matched_book

            # b) Búsqueda por texto (título, autor, sinopsis)
            text_books = (
                Book.objects.filter(
                    Q(title__icontains=q)
                    | Q(author__name__icontains=q)
                    | Q(authors__name__icontains=q)
                    | Q(description__icontains=q)
                )
                .select_related('author')
                .prefetch_related('categories', 'authors')
                .distinct()[:limit]
            )
            for b in text_books:
                if b.id not in books_set:
                    books_set[b.id] = b

            selected_books = list(books_set.values())[:limit]
            books_data = BookSerializer(selected_books, many=True, context={'request': request}).data

        # 2. Búsqueda de Autores
        if type_filter in ('all', 'authors'):
            authors = (
                Author.objects.filter(
                    Q(name__icontains=q)
                    | Q(canonical_name__icontains=q)
                    | Q(biography__icontains=q)
                )
                .prefetch_related('books')
                .distinct()[:limit]
            )
            authors_data = AuthorSerializer(authors, many=True, context={'request': request}).data

        # 3. Búsqueda de Usuarios (Lectores) con Privacidad
        if type_filter in ('all', 'users'):
            users_qs = (
                User.objects.filter(is_active=True)
                .filter(
                    Q(username__icontains=q)
                    | Q(first_name__icontains=q)
                    | Q(last_name__icontains=q)
                )
                .distinct()[: limit * 2]
            )
            visible_users = []
            for u in users_qs:
                if PrivacyService.can_view_profile(request.user, u):
                    visible_users.append(u)
                    if len(visible_users) >= limit:
                        break

            users_data = UserBasicSerializer(visible_users, many=True, context={'request': request}).data

        total = len(books_data) + len(authors_data) + len(users_data)

        return Response({
            'query': q,
            'type': type_filter,
            'total_results': total,
            'books': books_data,
            'authors': authors_data,
            'users': users_data,
        })

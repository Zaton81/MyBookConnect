"""
Vistas de Descubrimiento de Libros (Fase 20 — Descubrimiento de Libros).
Proporciona endpoints públicos y optimizados para explorar tendencias, libros populares,
novedades, géneros literarios y estadísticas de la plataforma sin forzar el uso de IA.
"""

import logging

from django.db.models import Count
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from books import services
from books.cache_utils import safe_cache_get, safe_cache_set
from books.media_utils import build_media_url
from books.models import Book, Category, Review

logger = logging.getLogger('mybookconnect.discovery')


def _serialize_book_card(book: Book, request=None) -> dict:
    """Helper ligero para serializar tarjetas de libros en descubrimiento."""
    author_name = book.author.name if book.author else 'Autor desconocido'
    cover_url = build_media_url(book.cover.name if book.cover else None, request=request)
    category_list = [c.name for c in book.categories.all()[:3]]

    return {
        'id': book.id,
        'title': book.title,
        'author_name': author_name,
        'author_id': book.author_id,
        'cover': cover_url,
        'average_rating': float(book.average_rating or 0.0),
        'ratings_count': getattr(book, 'ratings_count', 0) or 0,
        'categories': category_list,
        'description': (book.description[:240] + '...') if book.description and len(book.description) > 240 else (book.description or ''),
        'published_year': book.published_date.year if book.published_date else None,
    }


class BookDiscoveryView(APIView):
    """
    Vista unificada de descubrimiento de libros.
    Accesible para todos los usuarios (anónimos o autenticados).
    GET /api/v1/books/discover/
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Descubrimiento literario multifacético",
        description=(
            "Devuelve tendencias ponderadas, libros populares por lectores, novedades del catálogo, "
            "categorías activas y estadísticas públicas de la comunidad."
        ),
        responses={
            200: inline_serializer(
                name='BookDiscoveryResponse',
                fields={
                    'trending': serializers.ListField(child=serializers.DictField()),
                    'popular': serializers.ListField(child=serializers.DictField()),
                    'newest': serializers.ListField(child=serializers.DictField()),
                    'categories': serializers.ListField(child=serializers.DictField()),
                    'genre_books': serializers.ListField(child=serializers.DictField(), required=False),
                    'active_genre': serializers.CharField(allow_null=True),
                    'stats': serializers.DictField(),
                },
            ),
        },
        tags=['Books'],
    )
    def get(self, request):
        genre_param = request.query_params.get('genre', '').strip()
        try:
            limit = min(int(request.query_params.get('limit', 8)), 24)
        except ValueError:
            limit = 8

        cache_key = f"books:discovery:v1:{genre_param}:{limit}"
        cached_data = safe_cache_get(cache_key)
        if cached_data is not None:
            return Response(cached_data, status=status.HTTP_200_OK)

        # 1. Tendencias (Fase 23 algorithm con decaimiento temporal)
        trending_raw = services.get_trending_books(period='week', limit=limit, request=request)
        if not trending_raw:
            # Fallback en caso de base de datos nueva sin interacciones
            fallback_qs = (
                Book.objects.select_related('author')
                .prefetch_related('categories')
                .order_by('-average_rating', '-id')[:limit]
            )
            trending_raw = [_serialize_book_card(b, request) for b in fallback_qs]

        # 2. Populares (Mayor cantidad de lectores en estanterías o valoraciones)
        popular_qs = (
            Book.objects.select_related('author')
            .prefetch_related('categories')
            .annotate(readers_count=Count('user_entries'))
            .order_by('-readers_count', '-average_rating', '-id')[:limit]
        )
        popular = [_serialize_book_card(b, request) for b in popular_qs]

        # 3. Novedades (Últimos añadidos al catálogo)
        newest_qs = (
            Book.objects.select_related('author')
            .prefetch_related('categories')
            .order_by('-created_at', '-id')[:limit]
        )
        newest = [_serialize_book_card(b, request) for b in newest_qs]

        # 4. Categorías con libros
        cats_qs = (
            Category.objects.annotate(books_count=Count('books'))
            .filter(books_count__gt=0)
            .order_by('-books_count', 'name')[:16]
        )
        categories = [
            {'id': c.id, 'name': c.name, 'slug': c.slug, 'books_count': c.books_count}
            for c in cats_qs
        ]

        # 5. Libros por género si se solicita
        genre_books = []
        active_genre_name = None
        if genre_param:
            genre_filter_qs = Book.objects.select_related('author').prefetch_related('categories')
            if genre_param.isdigit():
                genre_filter_qs = genre_filter_qs.filter(categories__id=int(genre_param))
            else:
                genre_filter_qs = genre_filter_qs.filter(categories__slug=genre_param)

            matched_books = genre_filter_qs.order_by('-average_rating', '-id')[:limit]
            genre_books = [_serialize_book_card(b, request) for b in matched_books]
            if categories:
                matched_cat = next(
                    (c for c in categories if str(c['id']) == genre_param or c['slug'] == genre_param),
                    None
                )
                if matched_cat:
                    active_genre_name = matched_cat['name']

        # 6. Estadísticas globales para Landing
        total_books = Book.objects.count()
        total_reviews = Review.objects.count()
        stats = {
            'total_books': total_books,
            'total_reviews': total_reviews,
        }

        response_data = {
            'trending': trending_raw,
            'popular': popular,
            'newest': newest,
            'categories': categories,
            'genre_books': genre_books,
            'active_genre': active_genre_name or (genre_param if genre_param else None),
            'stats': stats,
        }

        # Cachear por 10 minutos (600 segundos)
        safe_cache_set(cache_key, response_data, timeout=600)

        return Response(response_data, status=status.HTTP_200_OK)

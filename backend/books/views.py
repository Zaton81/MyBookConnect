import logging

from django.core.cache import cache
from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .cache_utils import TTL_BOOK_DETAIL, book_detail_key
from .media_utils import build_media_url
from .models import (
    Author,
    Book,
    Errata,
    ErrataStatus,
    ReadingList,
    ReadingListFollow,
    ReadingListItem,
    ReadingListPrivacy,
    Review,
    ReviewComment,
    ReviewLike,
    UserBook,
)
from .pagination import StandardResultsSetPagination
from .serializers import (
    AuthorSerializer,
    BookSerializer,
    ErrataSerializer,
    ReadingListCreateUpdateSerializer,
    ReadingListItemSerializer,
    ReadingListSerializer,
    RecommendationFeedbackSerializer,
    ReviewCommentSerializer,
    ReviewSerializer,
    UnifiedSearchResponseSerializer,
    UnifiedSearchResultSerializer,
    UserBookSerializer,
)


class BookListCreateView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        queryset = Book.objects.select_related('author').prefetch_related('categories')
        q = self.request.query_params.get('q') or self.request.query_params.get('search')
        if not q:
            return queryset

        clean_q = q.strip()
        if not clean_q:
            return queryset

        engine = services.UnifiedSearchEngine(mode='hybrid')
        return engine.search_queryset(
            query=clean_q,
            auto_import=True,
        )

    def perform_create(self, serializer):
        serializer.save()


class AuthorListCreateView(generics.ListCreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)


class AuthorDetailView(generics.RetrieveAPIView):
    """
    Vista de detalle de autor.
    Rellena de forma proactiva biografía y fotografía si faltan, consultando
    múltiples proveedores externos (Wikipedia, Wikidata, OpenLibrary).
    """
    queryset = Author.objects.all().prefetch_related('books')
    serializer_class = AuthorSerializer
    permission_classes = (permissions.AllowAny,)

    def retrieve(self, request, *args, **kwargs):
        instance: Author = self.get_object()
        # Enriquecer biografía y foto si falta cualquiera de los dos o no se ha intentado
        if not instance.enrichment_attempted or not instance.photo or not instance.biography:
            try:
                services.maybe_enrich_author(instance)
                instance.enrichment_attempted = True
                instance.save(update_fields=['enrichment_attempted'])
                instance.refresh_from_db()
            except Exception as e:
                logging.exception(e)
                instance.enrichment_attempted = True
                instance.save(update_fields=['enrichment_attempted'])

        # En segundo plano, buscar e importar más libros del autor si no se ha hecho recientemente
        if instance.name:
            bg_author_key = f"bg_author_books_{instance.id}"
            if not cache.get(bg_author_key):
                try:
                    from .tasks import import_books_by_author_task

                    import_books_by_author_task.delay(instance.name)
                    cache.set(bg_author_key, True, 3600)  # Cooldown de 1 hora
                except Exception as exc:
                    logging.warning(f"No se pudo encolar import_books_by_author_task para {instance.name}: {exc}")

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class AuthorBooksView(APIView):
    """Listar todos los libros de un autor guardados localmente."""
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Libros de un autor",
        description="Lista los libros de un autor registrados localmente e incluye libros externos si aplica.",
        responses={200: OpenApiResponse(description="Libros locales y externos del autor")},
        tags=['Authors'],
    )
    def get(self, request, pk):
        books = Book.objects.filter(author_id=pk).select_related('author')
        local = BookSerializer(books, many=True).data

        # En segundo plano, asegurar búsqueda de más libros del autor si no se ha hecho recientemente
        bg_author_key = f"bg_author_books_{pk}"
        if not cache.get(bg_author_key):
            try:
                author_obj = Author.objects.filter(pk=pk).first()
                if author_obj and author_obj.name:
                    from .tasks import import_books_by_author_task

                    import_books_by_author_task.delay(author_obj.name)
                    cache.set(bg_author_key, True, 3600)
            except Exception as exc:
                logging.warning(f"No se pudo encolar import_books_by_author_task para autor {pk}: {exc}")

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
    """
    Vista de detalle de libro.
    Detecta automáticamente si falta portada, autor, sinopsis o categorías,
    disparando el enriquecimiento asíncrono para mantener el catálogo completo.
    """
    queryset = Book.objects.select_related('author').prefetch_related('categories')
    serializer_class = BookSerializer
    permission_classes = (permissions.AllowAny,)

    def retrieve(self, request, *args, **kwargs):
        book_id = kwargs.get('pk')
        cache_key = book_detail_key(book_id)

        # Si ya está en caché, servirlo de inmediato y verificar si le falta algún dato
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            if not cached_data.get('cover'):
                bg_cover_key = f"bg_cover_search_{book_id}"
                if not cache.get(bg_cover_key):
                    try:
                        from .tasks import download_cover_task

                        download_cover_task.delay(int(book_id))
                        cache.set(bg_cover_key, True, 600)  # Cooldown de 10 minutos
                    except Exception as exc:
                        logging.warning(f"No se pudo encolar download_cover_task para libro {book_id}: {exc}")

            missing_cached_meta = (
                not cached_data.get('author')
                or not cached_data.get('description')
                or not cached_data.get('categories')
            )
            if missing_cached_meta:
                bg_enrich_key = f"bg_enrich_book_{book_id}"
                if not cache.get(bg_enrich_key):
                    try:
                        from .tasks import enrich_book_task

                        enrich_book_task.delay(int(book_id))
                        cache.set(bg_enrich_key, True, 600)  # Cooldown de 10 minutos
                    except Exception as exc:
                        logging.warning(f"No se pudo encolar enrich_book_task para libro {book_id}: {exc}")
            return Response(cached_data)

        instance = self.get_object()
        # Si el libro no tiene portada, intentar descargarla en segundo plano
        if not instance.cover:
            bg_cover_key = f"bg_cover_search_{instance.id}"
            if not cache.get(bg_cover_key):
                try:
                    from .tasks import download_cover_task

                    download_cover_task.delay(instance.id)
                    cache.set(bg_cover_key, True, 600)  # Cooldown de 10 minutos
                except Exception as exc:
                    logging.warning(f"No se pudo encolar download_cover_task para libro {instance.id}: {exc}")

        # Si al libro le falta autor, sinopsis o categorías, enriquecer en segundo plano
        missing_metadata = (
            not instance.author
            or not instance.description
            or not instance.categories.exists()
        )
        if missing_metadata:
            bg_enrich_key = f"bg_enrich_book_{instance.id}"
            if not cache.get(bg_enrich_key):
                try:
                    from .tasks import enrich_book_task

                    enrich_book_task.delay(instance.id)
                    cache.set(bg_enrich_key, True, 600)  # Cooldown de 10 minutos
                except Exception as exc:
                    logging.warning(f"No se pudo encolar enrich_book_task para libro {instance.id}: {exc}")

        serializer = self.get_serializer(instance)
        data = serializer.data
        cache.set(cache_key, data, timeout=TTL_BOOK_DETAIL)
        return Response(data)


class UserBookPagination(StandardResultsSetPagination):
    pass


class UserBookListCreateView(generics.ListCreateAPIView):
    serializer_class = UserBookSerializer
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = UserBookPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return UserBook.objects.none()
        queryset = UserBook.objects.filter(user=self.request.user).select_related('book', 'book__author').prefetch_related('book__categories')
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

        status = params.get('status')
        if status and status in ('want_to_read', 'reading', 'read', 'abandoned'):
            queryset = queryset.filter(status=status)

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
            'progress', '-progress',
            'current_page', '-current_page',
            'started_at', '-started_at',
            'status', '-status',
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

    @extend_schema(
        summary="Obtener estado de lectura del libro para el usuario autenticado",
        responses={200: UserBookSerializer, 404: OpenApiResponse(description="No encontrado")},
        tags=['Books'],
    )
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
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        from django.db.models import Count, Exists, OuterRef, Q

        from users.policies import filter_visible_reviews

        queryset = (
            Review.objects.select_related('user', 'book', 'book__author')
            .prefetch_related('book__categories')
            .annotate(
                annotated_likes_count=Count('likes', distinct=True),
                annotated_comments_count=Count('comments', filter=Q(comments__deleted_at__isnull=True), distinct=True),
            )
            .order_by('-created_at')
        )

        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)

        user = self.request.user
        if user.is_authenticated:
            following_subquery = user.following.filter(pk=OuterRef('user_id'))
            user_liked_subquery = ReviewLike.objects.filter(review=OuterRef('pk'), user=user)
            queryset = queryset.annotate(
                is_friend=Exists(following_subquery),
                annotated_user_has_liked=Exists(user_liked_subquery),
            )

        return filter_visible_reviews(user, queryset)


    def create(self, request, *args, **kwargs):
        from rest_framework import status

        book_id = request.data.get('book_id') or request.data.get('book')
        if not book_id:
            return Response({'detail': 'book_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        rating = request.data.get('rating')
        try:
            rating_val = int(rating)
            if not (1 <= rating_val <= 10):
                raise ValueError()
        except (ValueError, TypeError):
            return Response({'detail': 'La puntuación debe ser un valor entre 1 y 10'}, status=status.HTTP_400_BAD_REQUEST)

        title = request.data.get('title', '')
        text = request.data.get('text', '')

        active_review = Review.objects.filter(user=request.user, book_id=book_id, deleted_at__isnull=True).first()
        if active_review:
            active_review.rating = rating_val
            active_review.title = title
            active_review.text = text
            active_review.save()
            review = active_review
            created = False
        else:
            review = Review.objects.create(
                user=request.user,
                book_id=book_id,
                rating=rating_val,
                title=title,
                text=text,
            )
            created = True
        serializer = self.get_serializer(review)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)


class ReviewDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ReviewSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated and (getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
            return Review.all_objects.select_related('user', 'book')
        return Review.objects.filter(deleted_at__isnull=True).select_related('user', 'book')

    def check_object_permissions(self, request, obj):
        super().check_object_permissions(request, obj)
        from rest_framework.exceptions import PermissionDenied

        from users.policies import can_edit_review, can_view_review

        if request.method in permissions.SAFE_METHODS:
            if not can_view_review(request.user, obj):
                raise PermissionDenied('No tienes permiso para ver esta reseña.')
        else:
            if not can_edit_review(request.user, obj):
                raise PermissionDenied('No tienes permiso para modificar esta reseña.')

    def perform_destroy(self, instance):
        instance.delete()


class ReviewLikeToggleView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Alternar like en una reseña",
        description="Marca o desmarca un like en la reseña indicada para el usuario autenticado.",
        responses={
            200: inline_serializer(
                name='ReviewLikeToggleResponse',
                fields={
                    'liked': serializers.BooleanField(),
                    'likes_count': serializers.IntegerField(),
                },
            ),
            403: OpenApiResponse(description="Bloqueo o sin permisos"),
            404: OpenApiResponse(description="Reseña no encontrada"),
        },
        tags=['Reviews'],
    )
    def post(self, request, review_id):
        from rest_framework.exceptions import PermissionDenied

        from users.models import Notification, NotificationType
        from users.policies import can_view_review

        review = get_object_or_404(Review.objects.select_related('user', 'book'), id=review_id)
        if not can_view_review(request.user, review):
            raise PermissionDenied('No tienes permiso para ver esta reseña.')

        if (
            review.user.blocked_users.filter(id=request.user.id).exists()
            or request.user.blocked_users.filter(id=review.user_id).exists()
        ):
            return Response({'detail': 'No puedes interactuar con esta reseña.'}, status=403)

        like = ReviewLike.objects.filter(user=request.user, review=review).first()
        if like:
            like.delete()
            liked = False
        else:
            ReviewLike.objects.create(user=request.user, review=review)
            liked = True
            if review.user_id != request.user.id:
                Notification.objects.create(
                    recipient=review.user,
                    actor=request.user,
                    type=NotificationType.LIKE,
                    title=f"{request.user.username} le dio me gusta a tu reseña",
                    message=f"A {request.user.username} le gustó tu reseña de '{review.book.title}'",
                    link=f"/books/{review.book_id}?review={review.id}",
                )

        return Response({
            'liked': liked,
            'likes_count': review.likes.count(),
        })


class ReviewCommentListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    @extend_schema(
        summary="Listar comentarios de una reseña",
        responses={200: ReviewCommentSerializer(many=True)},
        tags=['Reviews'],
    )
    def get(self, request, review_id):
        from rest_framework.exceptions import PermissionDenied

        from users.policies import can_view_review

        review = get_object_or_404(Review.objects.select_related('user'), id=review_id)
        if not can_view_review(request.user, review):
            raise PermissionDenied('No tienes permiso para ver esta reseña.')

        comments = (
            ReviewComment.objects.filter(review=review, deleted_at__isnull=True)
            .select_related('user')
            .order_by('created_at')
        )

        if request.user.is_authenticated:
            blocked_by_user = set(request.user.blocked_users.values_list('id', flat=True))
            blocking_user = set(request.user.blocked_by.values_list('id', flat=True))
            excluded = blocked_by_user.union(blocking_user)
            if excluded:
                comments = comments.exclude(user_id__in=excluded)

        serializer = ReviewCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Publicar comentario en una reseña",
        request=inline_serializer(
            name='ReviewCommentCreateRequest',
            fields={'content': serializers.CharField()},
        ),
        responses={201: ReviewCommentSerializer, 400: OpenApiResponse(description="Validación fallida")},
        tags=['Reviews'],
    )
    def post(self, request, review_id):
        from rest_framework import status
        from rest_framework.exceptions import PermissionDenied

        from users.models import Notification, NotificationType
        from users.policies import can_view_review

        if not request.user.is_authenticated:
            return Response({'detail': 'Autenticación requerida.'}, status=status.HTTP_401_UNAUTHORIZED)

        review = get_object_or_404(Review.objects.select_related('user', 'book'), id=review_id)
        if not can_view_review(request.user, review):
            raise PermissionDenied('No tienes permiso para ver esta reseña.')

        if (
            review.user.blocked_users.filter(id=request.user.id).exists()
            or request.user.blocked_users.filter(id=review.user_id).exists()
        ):
            return Response({'detail': 'No puedes interactuar con esta reseña.'}, status=status.HTTP_403_FORBIDDEN)

        content = (request.data.get('content') or '').strip()
        if not content:
            return Response({'detail': 'El comentario no puede estar vacío.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(content) > 1000:
            return Response({'detail': 'El comentario excede el máximo permitido (1000 caracteres).'}, status=status.HTTP_400_BAD_REQUEST)

        comment = ReviewComment.objects.create(
            user=request.user,
            review=review,
            content=content,
        )

        if review.user_id != request.user.id:
            Notification.objects.create(
                recipient=review.user,
                actor=request.user,
                type=NotificationType.COMMENT,
                title=f"{request.user.username} comentó en tu reseña",
                message=content[:120],
                link=f"/books/{review.book_id}?review={review.id}",
            )

        serializer = ReviewCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReviewCommentDeleteView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Eliminar comentario de reseña",
        description="Aplica borrado lógico sobre el comentario.",
        responses={204: OpenApiResponse(description="Comentario eliminado con éxito")},
        tags=['Reviews'],
    )
    def delete(self, request, review_id, comment_id):
        from rest_framework import status

        comment = get_object_or_404(ReviewComment, id=comment_id, review_id=review_id, deleted_at__isnull=True)

        if comment.user_id != request.user.id and not request.user.is_staff and not request.user.is_superuser:
            return Response({'detail': 'No tienes permiso para eliminar este comentario.'}, status=status.HTTP_403_FORBIDDEN)

        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



class ImportBookView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Importar libro desde proveedores externos",
        description="Busca e importa libros por ISBN o título utilizando Google Books u OpenLibrary.",
        request=inline_serializer(
            name='ImportBookRequest',
            fields={
                'isbn': serializers.CharField(required=False),
                'title': serializers.CharField(required=False),
                'offset': serializers.IntegerField(required=False, default=0),
            },
        ),
        responses={
            201: BookSerializer,
            400: OpenApiResponse(description="Parámetros inválidos"),
            404: OpenApiResponse(description="No se encontraron resultados"),
        },
        tags=['Books'],
    )
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


class UserRecommendationsView(APIView):
    """
    Endpoint para obtener recomendaciones personalizadas de libros para el usuario autenticado.
    Soporta estrategias de scoring: 'hybrid' (por defecto), 'rules', 'social', 'semantic'.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Recomendaciones personalizadas de libros",
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                default=10,
                description="Cantidad máxima de recomendaciones a devolver (1-30).",
            ),
            OpenApiParameter(
                name='strategy',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                default='v1',
                description="Estrategia de cálculo: 'v1' (ponderación canónica), 'hybrid', 'rules', 'social', 'semantic'.",
            ),
            OpenApiParameter(
                name='version',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                default='v1',
                description="Versión del motor de recomendaciones (ej. 'v1').",
            ),
        ],
        responses={200: inline_serializer(
            name='UserRecommendationResponse',
            fields={
                'count': serializers.IntegerField(),
                'strategy': serializers.CharField(),
                'algorithm_version': serializers.CharField(),
                'results': serializers.ListField(child=serializers.DictField()),
            },
        )},
        tags=['Books'],
    )
    def get(self, request):
        limit = request.query_params.get('limit', 10)
        try:
            limit = max(1, min(30, int(limit)))
        except (ValueError, TypeError):
            limit = 10

        version_param = request.query_params.get('version', 'v1').lower().strip()
        strategy = request.query_params.get('strategy')
        if not strategy:
            if version_param == 'v2':
                strategy = 'v2'
            elif version_param == 'v1':
                strategy = 'v1'
            else:
                strategy = 'hybrid'
        else:
            strategy = strategy.lower().strip()

        if strategy not in ('v1', 'canonical_v1', 'v2', 'collab', 'collaborative', 'hybrid', 'rules', 'social', 'semantic'):
            strategy = 'v2' if version_param == 'v2' else 'v1'

        results = services.get_user_recommendations(
            user=request.user,
            limit=limit,
            strategy=strategy,
            request=request,
        )
        algo_version = 'v2' if (strategy in ('v2', 'collab', 'collaborative') or version_param == 'v2') else 'v1'
        return Response({
            'count': len(results),
            'strategy': strategy,
            'algorithm_version': algo_version,
            'results': results,
        })


class SimilarReadersView(APIView):
    """
    Endpoint para consultar a los usuarios lectores con gustos más similares (vecinos K-NN v2).
    Calcula similitud a partir de libros compartidos y congruencia en valoraciones.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Lectores con gustos literarios similares",
        description="Devuelve la lista de lectores afines con su coeficiente de similitud y obras compartidas.",
        parameters=[
            OpenApiParameter(
                name='limit',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                default=10,
                description="Cantidad máxima de lectores a devolver (máx 30).",
            ),
        ],
        responses={200: inline_serializer(
            name='SimilarReadersResponse',
            fields={
                'count': serializers.IntegerField(),
                'results': serializers.ListField(child=serializers.DictField()),
            },
        )},
        tags=['Books'],
    )
    def get(self, request):
        limit = request.query_params.get('limit', 10)
        try:
            limit = max(1, min(30, int(limit)))
        except (ValueError, TypeError):
            limit = 10

        results = services.get_similar_readers(user=request.user, limit=limit)
        return Response({
            'count': len(results),
            'results': results,
        })


class RecommendationView(APIView):
    """
    Endpoint para obtener recomendaciones contextuales a partir de un libro específico (Item-to-Item).
    Combina filtrado colaborativo ("quienes leyeron X también leyeron Y") con afinidad temática.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Recomendaciones basadas en un libro específico",
        responses={200: BookSerializer(many=True)},
        tags=['Books'],
    )
    def get(self, request, pk):
        limit = request.query_params.get('limit', 6)
        try:
            limit = max(1, min(20, int(limit)))
        except (ValueError, TypeError):
            limit = 6

        results = services.get_book_recommendations(
            book_id=pk,
            limit=limit,
            user=request.user,
            request=request,
        )
        return Response(results)


class RecommendationFeedbackView(APIView):
    """
    Endpoint para registrar eventos de interacción sobre libros recomendados.
    Soporta eventos individuales (dict) o por lotes (list) para registrar
    múltiples impresiones simultáneamente al mostrar recomendaciones.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Registrar feedback de recomendaciones",
        request=inline_serializer(
            name='RecommendationFeedbackInput',
            fields={
                'book_id': serializers.IntegerField(),
                'action': serializers.CharField(),
                'recommendation_id': serializers.CharField(required=False),
                'strategy': serializers.CharField(required=False),
                'algorithm_version': serializers.CharField(required=False),
                'metadata': serializers.DictField(required=False),
            },
        ),
        responses={201: RecommendationFeedbackSerializer(many=True)},
        tags=['Books'],
    )
    def post(self, request):
        """
        Procesa el registro de uno o varios eventos de retroalimentación de recomendaciones.

        :param request: Objeto HttpRequest que contiene los datos del evento en request.data.
        :return: Response con el recuento de eventos registrados y los datos serializados.
        """
        payload = request.data
        if not payload:
            return Response(
                {'detail': 'El cuerpo de la petición no puede estar vacío.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items = payload if isinstance(payload, list) else [payload]
        created_records = []

        for item in items:
            book_id = item.get('book_id')
            action = item.get('action')
            if not book_id or not action:
                return Response(
                    {'detail': 'Los campos "book_id" y "action" son obligatorios en cada evento.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            recommendation_id = item.get('recommendation_id', '')
            strategy = item.get('strategy', 'hybrid')
            algorithm_version = item.get('algorithm_version', 'v1.0')
            metadata = item.get('metadata') or {}

            try:
                feedback = services.record_recommendation_event(
                    user=request.user,
                    book_id=book_id,
                    action=action,
                    recommendation_id=recommendation_id,
                    strategy=strategy,
                    algorithm_version=algorithm_version,
                    metadata=metadata,
                )
                created_records.append(feedback)
            except ValueError as val_err:
                return Response({'detail': str(val_err)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as exc:
                logging.exception("Error al registrar feedback de recomendación: %s", exc)
                return Response(
                    {'detail': 'Error interno al registrar el evento.'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        serializer = RecommendationFeedbackSerializer(created_records, many=True)
        return Response(
            {'status': 'success', 'count': len(created_records), 'data': serializer.data},
            status=status.HTTP_201_CREATED,
        )


class RecommendationMetricsView(APIView):
    """
    Endpoint para consultar métricas y analítica de conversión de recomendaciones
    (CTR, tasa de guardado en wishlist, inicio y finalización de lectura).
    Permite filtrar por estrategia, versión de algoritmo y ventana temporal.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Métricas de conversión de recomendaciones",
        responses={200: inline_serializer(
            name='RecommendationMetricsResponse',
            fields={
                'strategy': serializers.CharField(),
                'metrics': serializers.DictField(),
            },
        )},
        tags=['Books'],
    )
    def get(self, request):
        """
        Calcula y retorna los indicadores de rendimiento de recomendaciones según los filtros especificados.

        :param request: Objeto HttpRequest con parámetros de consulta opcionales (strategy, algorithm_version, days, scope).
        :return: Response con métricas agregadas (totales, ratios y desgloses).
        """
        strategy = request.query_params.get('strategy')
        algorithm_version = request.query_params.get('algorithm_version')
        days_str = request.query_params.get('days')
        scope = request.query_params.get('scope', 'global').lower().strip()

        days = None
        if days_str:
            try:
                days = int(days_str)
            except ValueError:
                days = None

        # Si el usuario no es staff/editor y pide scope global, o si especifica scope='me', filtramos por su usuario
        user_filter = None
        if scope == 'me' or not (request.user.is_staff or getattr(request.user, 'is_editor', False)):
            user_filter = request.user

        metrics = services.get_recommendation_metrics(
            user=user_filter,
            strategy=strategy,
            algorithm_version=algorithm_version,
            days=days,
        )
        return Response(metrics, status=status.HTTP_200_OK)


class AuthorBookRefreshView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Actualizar libros de un autor",
        description="Sincroniza y busca nuevos libros externos para el autor especificado.",
        responses={
            200: inline_serializer(
                name='AuthorBookRefreshResponse',
                fields={'count': serializers.IntegerField(), 'detail': serializers.CharField()},
            ),
            404: OpenApiResponse(description="Autor no encontrado"),
        },
        tags=['Authors'],
    )
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
        if getattr(self, 'swagger_fake_view', False) or not self.request.user.is_authenticated:
            return Errata.objects.none()
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

    @extend_schema(
        summary="Feed de actividad social comunitaria",
        description="Retorna las últimas lecturas y reseñas realizadas en la plataforma.",
        responses={
            200: OpenApiResponse(description="Lista combinada de actividad social reciente"),
        },
        tags=['Social'],
    )
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
                    'avatar': build_media_url(r.user.avatar, request=request),
                },
                'book': {
                    'id': r.book.id,
                    'title': r.book.title,
                    'cover': build_media_url(r.book.cover, request=request),
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
                    'avatar': build_media_url(ub.user.avatar, request=request),
                },
                'book': {
                    'id': ub.book.id,
                    'title': ub.book.title,
                    'cover': build_media_url(ub.book.cover, request=request),
                    'author_name': ub.book.author.name if ub.book.author else '',
                },
                'rating': ub.rating,
            })

        items.sort(key=lambda x: x['timestamp'], reverse=True)
        return Response({'results': items[:20]})


class TrendingBooksView(APIView):
    """
    Libros en tendencia en la plataforma basados en el algoritmo de decaimiento temporal (Fase 23).
    Acepta parámetro query `?period=week|month|year|all` (por defecto 'week').
    Resuelve dinámicamente las URLs de medios absolutas y emplea caché Redis por periodo.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Libros en tendencia",
        responses={200: inline_serializer(
            name='TrendingBooksResponse',
            fields={
                'period': serializers.CharField(),
                'results': serializers.ListField(child=serializers.DictField()),
            },
        )},
        tags=['Books'],
    )
    def get(self, request):
        period = request.query_params.get('period', 'week')
        results = services.get_trending_books(period=period, limit=12, request=request)
        return Response({'results': results, 'period': period})


class ReadingMatchView(APIView):
    """
    Calcula el porcentaje de afinidad literaria y libros compartidos entre usuarios.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Afinidad literaria entre usuarios",
        responses={200: inline_serializer(
            name='ReadingMatchResponse',
            fields={
                'match_percentage': serializers.IntegerField(),
                'is_self': serializers.BooleanField(),
                'common_books': serializers.ListField(child=serializers.DictField()),
            },
        )},
        tags=['Books'],
    )
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
            'cover': build_media_url(b.cover, request=request),
            'author_name': b.author.name if b.author else '',
        } for b in common_books]

        return Response({
            'match_percentage': match_percentage,
            'common_books_count': len(common_ids),
            'common_books': common_serialized,
            'my_read_count': len(my_books),
            'their_read_count': len(their_books),
        })


class ReadingListViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión integral de Listas de Lectura (Fase 21).
    Soporta:
    - CRUD de listas con permisos (solo el creador puede editar o eliminar).
    - Filtrado por privacidad (públicas, solo seguidores, privadas).
    - Acciones para añadir, quitar y reordenar libros.
    - Seguir y dejar de seguir listas.
    - Consulta de listas públicas o de usuarios seguidos.
    """
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        user = self.request.user
        queryset = ReadingList.objects.select_related('user').prefetch_related(
            'items__book', 'items__book__author', 'followers'
        )

        user_id_param = self.request.query_params.get('user_id')
        if user_id_param:
            queryset = queryset.filter(user_id=user_id_param)

        if self.request.query_params.get('my_lists') == 'true' and user.is_authenticated:
            return queryset.filter(user=user)

        if self.request.query_params.get('followed') == 'true' and user.is_authenticated:
            return queryset.filter(followers__user=user)

        if not user.is_authenticated:
            return queryset.filter(privacy=ReadingListPrivacy.PUBLIC)

        following_ids = user.following.values_list('id', flat=True)
        return queryset.filter(
            Q(user=user) |
            Q(privacy=ReadingListPrivacy.PUBLIC) |
            Q(privacy=ReadingListPrivacy.FOLLOWERS, user_id__in=following_ids)
        ).distinct()

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ReadingListCreateUpdateSerializer
        return ReadingListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo el creador puede editar esta lista.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo el creador puede eliminar esta lista.")
        instance.delete()

    @action(detail=True, methods=['post'], url_path='add-book', permission_classes=[permissions.IsAuthenticated])
    def add_book(self, request, pk=None):
        """Añade un libro a la lista en una posición específica o al final."""
        reading_list = self.get_object()
        if reading_list.user != request.user and not request.user.is_staff:
            return Response({'detail': 'No tienes permiso para modificar esta lista.'}, status=status.HTTP_403_FORBIDDEN)

        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'detail': 'El campo book_id es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        book = get_object_or_404(Book, id=book_id)

        if ReadingListItem.objects.filter(reading_list=reading_list, book=book).exists():
            return Response({'detail': 'Este libro ya se encuentra en la lista.'}, status=status.HTTP_400_BAD_REQUEST)

        position = request.data.get('position')
        if position is None:
            max_pos = reading_list.items.count()
            position = max_pos + 1

        notes = request.data.get('notes', '')

        item = ReadingListItem.objects.create(
            reading_list=reading_list,
            book=book,
            position=position,
            notes=notes,
        )

        return Response(ReadingListItemSerializer(item, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete', 'post'], url_path='remove-book', permission_classes=[permissions.IsAuthenticated])
    def remove_book(self, request, pk=None):
        """Elimina un libro de la lista de lectura."""
        reading_list = self.get_object()
        if reading_list.user != request.user and not request.user.is_staff:
            return Response({'detail': 'No tienes permiso para modificar esta lista.'}, status=status.HTTP_403_FORBIDDEN)

        book_id = request.data.get('book_id') or request.query_params.get('book_id')
        if not book_id:
            return Response({'detail': 'El parámetro book_id es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = ReadingListItem.objects.filter(reading_list=reading_list, book_id=book_id).delete()
        if deleted_count == 0:
            return Response({'detail': 'El libro no estaba en esta lista.'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'detail': 'Libro eliminado de la lista.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put', 'post'], url_path='reorder', permission_classes=[permissions.IsAuthenticated])
    def reorder(self, request, pk=None):
        """
        Reordena los libros de la lista. Acepta:
        [ {"book_id": 1, "position": 1}, {"book_id": 2, "position": 2} ] o [1, 2, 3] (lista ordenada de IDs).
        """
        reading_list = self.get_object()
        if reading_list.user != request.user and not request.user.is_staff:
            return Response({'detail': 'No tienes permiso para modificar esta lista.'}, status=status.HTTP_403_FORBIDDEN)

        orders = request.data.get('items') or request.data
        if not isinstance(orders, list):
            return Response({'detail': 'Se espera una lista de elementos para reordenar.'}, status=status.HTTP_400_BAD_REQUEST)

        for idx, entry in enumerate(orders, start=1):
            if isinstance(entry, dict):
                b_id = entry.get('book_id') or entry.get('id')
                pos = entry.get('position', idx)
            else:
                b_id = entry
                pos = idx

            ReadingListItem.objects.filter(reading_list=reading_list, book_id=b_id).update(position=pos)

        updated_list = ReadingList.objects.prefetch_related('items__book', 'items__book__author').get(pk=reading_list.pk)
        return Response(ReadingListSerializer(updated_list, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='follow', permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, pk=None):
        """Sigue una lista de lectura pública."""
        reading_list = self.get_object()
        if reading_list.user == request.user:
            return Response({'detail': 'No puedes seguir tu propia lista.'}, status=status.HTTP_400_BAD_REQUEST)

        follow_obj, created = ReadingListFollow.objects.get_or_create(
            user=request.user,
            reading_list=reading_list,
        )
        return Response({'detail': 'Ahora sigues esta lista.', 'created': created}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete', 'post'], url_path='unfollow', permission_classes=[permissions.IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Deja de seguir una lista de lectura."""
        reading_list = self.get_object()
        deleted_count, _ = ReadingListFollow.objects.filter(
            user=request.user,
            reading_list=reading_list,
        ).delete()
        return Response({'detail': 'Has dejado de seguir esta lista.', 'deleted': deleted_count > 0}, status=status.HTTP_200_OK)


class ReadingStatsView(APIView):
    """
    Vista de Estadísticas de Lectura (Fase 22).

    Devuelve métricas agregadas de lectura (libros leídos, en progreso, páginas,
    calificación promedio, desglose de géneros, ranking de autores y lectura por mes).
    Soporta consultar las estadísticas propias (usuario autenticado) o de otro usuario
    respetando su nivel de privacidad (público, solo amigos o privado).
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Estadísticas de lectura de usuario",
        responses={200: inline_serializer(
            name='ReadingStatsResponse',
            fields={
                'total_books': serializers.IntegerField(),
                'read_books': serializers.IntegerField(),
                'total_pages': serializers.IntegerField(),
                'genres': serializers.DictField(),
                'stats': serializers.DictField(),
            },
        )},
        tags=['Books'],
    )
    def get(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        user_id_param = request.query_params.get('user_id')
        if user_id_param:
            try:
                target_user = User.objects.get(id=int(user_id_param))
            except (ValueError, User.DoesNotExist):
                return Response({'detail': 'Usuario no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

            # Comprobar permisos de privacidad si se consulta a otro usuario
            is_self = request.user.is_authenticated and request.user.id == target_user.id
            is_staff = request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

            if not is_self and not is_staff:
                privacy = getattr(target_user, 'privacy_level', 'public')
                if privacy == 'private':
                    return Response({'detail': 'Este perfil es privado.'}, status=status.HTTP_403_FORBIDDEN)
                elif privacy in ('friends', 'friends_only'):
                    if not request.user.is_authenticated:
                        return Response({'detail': 'Inicia sesión para ver este perfil.'}, status=status.HTTP_401_UNAUTHORIZED)
                    # Comprobar seguimiento mutuo (amigos)
                    is_mutual = (
                        request.user.following.filter(id=target_user.id).exists()
                        and target_user.following.filter(id=request.user.id).exists()
                    )
                    if not is_mutual:
                        return Response({'detail': 'Estadísticas solo disponibles para amigos.'}, status=status.HTTP_403_FORBIDDEN)

            target_user_id = target_user.id
        else:
            if not request.user.is_authenticated:
                return Response({'detail': 'Autenticación requerida para ver tus estadísticas.'}, status=status.HTTP_401_UNAUTHORIZED)
            target_user_id = request.user.id

        stats = services.get_user_reading_stats(target_user_id)
        return Response(stats)


class UnifiedBookSearchView(APIView):
    """
    Endpoint de búsqueda unificada para libros.
    Combina en una sola canalización:
    - Búsqueda Textual (FTS PostgreSQL con ranking lexicográfico)
    - Búsqueda Difusa (Trigram similarity pg_trgm tolerante a erratas)
    - Búsqueda Semántica (Similitud coseno de vectores / embeddings con fallback temático)
    Soporta modos: 'hybrid' (predeterminado), 'text', 'fuzzy', 'semantic'.
    """
    permission_classes = (permissions.AllowAny,)

    @extend_schema(
        summary="Búsqueda unificada multicanal de libros",
        description=(
            "Realiza una búsqueda avanzada combinando análisis léxico (FTS), "
            "similitud difusa (trigramas) y similitud semántica (embeddings vectoriales). "
            "Permite desglosar el score de relevancia por canal y filtrar por autor, categoría y calificación mínima."
        ),
        parameters=[
            OpenApiParameter(
                name='q',
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Término o consulta de búsqueda (título, autor, sinopsis o concepto).",
            ),
            OpenApiParameter(
                name='mode',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                default='hybrid',
                description="Canal de búsqueda a priorizar: 'hybrid', 'text', 'fuzzy', 'semantic'.",
            ),
            OpenApiParameter(
                name='category',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Nombre o slug de la categoría a filtrar.",
            ),
            OpenApiParameter(
                name='author',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Nombre o ID del autor a filtrar.",
            ),
            OpenApiParameter(
                name='min_rating',
                type=float,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Calificación promedio mínima (ej. 4.0).",
            ),
            OpenApiParameter(
                name='page',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                default=1,
                description="Número de página (paginación 1-indexada).",
            ),
            OpenApiParameter(
                name='page_size',
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                default=20,
                description="Cantidad de resultados por página (máx 100).",
            ),
            OpenApiParameter(
                name='auto_import',
                type=bool,
                location=OpenApiParameter.QUERY,
                required=False,
                default=True,
                description="Habilitar importación automática de fuentes externas si no hay coincidencias.",
            ),
        ],
        responses={200: UnifiedSearchResponseSerializer},
        tags=['Books'],
    )
    def get(self, request, *args, **kwargs):
        query = (request.query_params.get('q') or '').strip()
        if not query:
            return Response(
                {
                    'query': '',
                    'mode': 'hybrid',
                    'count': 0,
                    'total': 0,
                    'page': 1,
                    'page_size': 20,
                    'results': [],
                },
                status=status.HTTP_200_OK,
            )

        mode = request.query_params.get('mode', 'hybrid').lower()
        if mode not in ('hybrid', 'text', 'fuzzy', 'semantic'):
            mode = 'hybrid'

        category = request.query_params.get('category')
        author = request.query_params.get('author')
        min_rating_param = request.query_params.get('min_rating')
        min_rating = None
        if min_rating_param:
            try:
                min_rating = float(min_rating_param)
            except (ValueError, TypeError):
                pass

        try:
            page = max(1, int(request.query_params.get('page', 1)))
        except (ValueError, TypeError):
            page = 1

        try:
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page_size = 20

        auto_import_param = (request.query_params.get('auto_import') or 'true').lower()
        auto_import = auto_import_param in ('true', '1', 'yes')

        offset = (page - 1) * page_size

        engine = services.UnifiedSearchEngine(mode=mode)
        items, total = engine.search(
            query=query,
            category=category,
            author=author,
            min_rating=min_rating,
            limit=page_size,
            offset=offset,
            auto_import=auto_import,
        )

        serializer = UnifiedSearchResultSerializer(items, many=True, context={'request': request})
        response_data = {
            'query': query,
            'mode': mode,
            'count': len(items),
            'total': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data,
        }
        return Response(response_data, status=status.HTTP_200_OK)





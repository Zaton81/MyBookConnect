import logging

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from mybookconnect.html_sanitizer import sanitize_plain_text
from mybookconnect.idempotency import idempotent
from users.throttles import CommentRateThrottle, LikeRateThrottle

from . import services
from .cache_utils import TTL_BOOK_DETAIL, book_detail_key
from .media_utils import build_media_url
from .models import (
    Author,
    AuthorAnnouncement,
    AuthorNewsletter,
    AuthorNewsletterIssue,
    AuthorNewsletterSubscriber,
    Book,
    Errata,
    ErrataStatus,
    ReadingList,
    ReadingListCollaborator,
    ReadingListComment,
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
    AuthorNewsletterCreateUpdateSerializer,
    AuthorNewsletterIssueCreateUpdateSerializer,
    AuthorNewsletterIssueSerializer,
    AuthorNewsletterSerializer,
    AuthorNewsletterSubscriberSerializer,
    AuthorSerializer,
    BookSerializer,
    ErrataSerializer,
    ReadingListCollaboratorSerializer,
    ReadingListCommentSerializer,
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

logger = logging.getLogger(__name__)


class BookListCreateView(generics.ListCreateAPIView):
    serializer_class = BookSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        queryset = Book.objects.select_related('author').prefetch_related('categories', 'authors')
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
    queryset = Book.objects.select_related('author').prefetch_related('categories', 'authors')
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
        params = self.request.query_params
        user_id = params.get('user_id')
        if user_id and str(user_id) != str(self.request.user.id):
            from django.contrib.auth import get_user_model
            from rest_framework.exceptions import NotFound, PermissionDenied

            from users.policies import are_mutually_blocked, can_view_reading_activity
            UserModel = get_user_model()
            target_user = get_object_or_404(UserModel, id=user_id)
            if are_mutually_blocked(self.request.user, target_user):
                raise NotFound("Usuario no encontrado.")
            if not can_view_reading_activity(self.request.user, target_user):
                raise PermissionDenied("La biblioteca de este usuario es privada.")
            queryset = UserBook.objects.filter(user=target_user)
        else:
            queryset = UserBook.objects.filter(user=self.request.user)

        queryset = queryset.select_related('book', 'book__author').prefetch_related('book__categories')

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book = serializer.validated_data.get('book')

        with transaction.atomic():
            user_book = UserBook.objects.select_for_update().filter(user=request.user, book=book).first()
            if user_book:
                for attr, val in serializer.validated_data.items():
                    if attr != 'book':
                        setattr(user_book, attr, val)
                user_book.save()
                return Response(self.get_serializer(user_book).data, status=status.HTTP_200_OK)

            try:
                with transaction.atomic():
                    user_book = serializer.save(user=request.user)
                return Response(self.get_serializer(user_book).data, status=status.HTTP_201_CREATED)
            except IntegrityError:
                # Recuperar limpiamente ante colisión concurrente de inserción
                user_book = UserBook.objects.select_for_update().filter(user=request.user, book=book).first()
                if user_book:
                    for attr, val in serializer.validated_data.items():
                        if attr != 'book':
                            setattr(user_book, attr, val)
                    user_book.save()
                    return Response(self.get_serializer(user_book).data, status=status.HTTP_200_OK)
                raise


class UserBookDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserBookSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self):
        return get_object_or_404(UserBook, pk=self.kwargs['pk'], user=self.request.user)

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.delete()


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
        from django.db.models import Count, Exists, OuterRef

        from users.policies import filter_visible_reviews

        queryset = (
            Review.objects.select_related('user', 'book', 'book__author')
            .prefetch_related('book__categories', 'book__authors')
            .annotate(
                annotated_likes_count=Count('likes', distinct=True),
                annotated_comments_count=Count('comments', filter=Q(comments__deleted_at__isnull=True), distinct=True),
            )
            .order_by('-created_at')
        )

        book_id = self.request.query_params.get('book')
        if book_id:
            queryset = queryset.filter(book_id=book_id)

        user_filter = self.kwargs.get('user_id') or self.request.query_params.get('user') or self.request.query_params.get('user_id')
        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        username_filter = self.request.query_params.get('username')
        if username_filter:
            queryset = queryset.filter(user__username__iexact=username_filter.strip())

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

        if request.user.is_authenticated and getattr(request.user, 'is_disciplinary_muted', False):
            return Response(
                {'detail': f"Tu cuenta se encuentra silenciada temporalmente por moderación hasta {request.user.muted_until}."},
                status=status.HTTP_403_FORBIDDEN,
            )

        book_id = request.data.get('book_id') or request.data.get('book')
        if not book_id:
            return Response({'detail': 'book_id es requerido'}, status=status.HTTP_400_BAD_REQUEST)

        rating = request.data.get('rating')
        try:
            rating_val = int(rating)
            if not (1 <= rating_val <= 5):
                raise ValueError()
        except (ValueError, TypeError):
            return Response({'detail': 'La puntuación debe ser un valor entre 1 y 5'}, status=status.HTTP_400_BAD_REQUEST)

        from mybookconnect.html_sanitizer import sanitize_html, sanitize_plain_text

        title = sanitize_plain_text(request.data.get('title', ''))
        text = sanitize_html(request.data.get('text', ''))
        image_file = request.FILES.get('image')

        if image_file:
            from django.core.exceptions import ValidationError as DjangoValidationError

            from mybookconnect.media_security import COVER_PRESET, sanitize_image, validate_cover_image
            try:
                validate_cover_image(image_file)
                image_file = sanitize_image(image_file, max_dimensions=COVER_PRESET)
            except DjangoValidationError as err:
                msg = err.messages if hasattr(err, 'messages') else str(err)
                return Response({'image': [msg]}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            active_review = Review.objects.select_for_update().filter(
                user=request.user, book_id=book_id, deleted_at__isnull=True
            ).first()

            if active_review:
                active_review.rating = rating_val
                active_review.title = title
                active_review.text = text
                if image_file is not None:
                    active_review.image = image_file
                active_review.save()
                review = active_review
                created = False
            else:
                try:
                    with transaction.atomic():
                        review = Review.objects.create(
                            user=request.user,
                            book_id=book_id,
                            rating=rating_val,
                            title=title,
                            text=text,
                            image=image_file,
                        )
                    created = True
                except IntegrityError:
                    # Colisión concurrente: otro worker/hilo creó la reseña simultáneamente
                    active_review = Review.objects.select_for_update().filter(
                        user=request.user, book_id=book_id, deleted_at__isnull=True
                    ).first()
                    if active_review:
                        active_review.rating = rating_val
                        active_review.title = title
                        active_review.text = text
                        if image_file is not None:
                            active_review.image = image_file
                        active_review.save()
                        review = active_review
                        created = False
                    else:
                        raise


            if created:
                try:
                    from books.services.gamification_service import GamificationService
                    GamificationService.evaluate_user_badges(request.user)
                except Exception as g_exc:
                    logger.debug(f"Error evaluando badges para usuario {request.user.id}: {g_exc}")

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
            if getattr(request.user, 'is_disciplinary_muted', False):
                raise PermissionDenied('Tu cuenta se encuentra silenciada temporalmente por moderación.')
            if not can_edit_review(request.user, obj):
                raise PermissionDenied('No tienes permiso para modificar esta reseña.')

    def perform_update(self, serializer):
        with transaction.atomic():
            serializer.save()

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance.delete()


class ReviewLikeToggleView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    throttle_classes = [LikeRateThrottle]

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

        from users.models import NotificationType
        from users.policies import can_view_review

        review = get_object_or_404(Review.objects.select_related('user', 'book'), id=review_id)
        if (
            review.user.blocked_users.filter(id=request.user.id).exists()
            or request.user.blocked_users.filter(id=review.user_id).exists()
        ):
            return Response({'detail': 'No puedes interactuar con esta reseña.'}, status=403)

        if not can_view_review(request.user, review):
            raise PermissionDenied('No tienes permiso para ver esta reseña.')

        with transaction.atomic():
            like = ReviewLike.objects.select_for_update().filter(user=request.user, review=review).first()
            if like:
                like.delete()
                liked = False
            else:
                try:
                    with transaction.atomic():
                        ReviewLike.objects.create(user=request.user, review=review)
                        liked = True
                except IntegrityError:
                    # Concurrencia: otro request simultáneo ya creó el like
                    liked = True

                if liked and review.user_id != request.user.id:
                    from users.models import NotificationType
                    from users.notification_service import NotificationService

                    NotificationService.send_notification(
                        recipient=review.user,
                        actor=request.user,
                        notif_type=NotificationType.LIKE,
                        title=f"{request.user.username} le dio me gusta a tu reseña",
                        message=f"A {request.user.username} le gustó tu reseña de '{review.book.title}'",
                        link=f"/books/{review.book_id}?review={review.id}",
                    )

                if liked:
                    try:
                        from users.activity_service import record_activity
                        from users.models import ActivityType
                        record_activity(
                            user=request.user,
                            activity_type=ActivityType.REVIEW_LIKED,
                            book=review.book,
                            review=review,
                            target_user=review.user,
                            metadata={'review_id': review.id, 'rating': review.rating},
                        )
                    except Exception:
                        pass

        return Response({
            'liked': liked,
            'likes_count': review.likes.count(),
        })


class ReviewCommentListCreateView(APIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_throttles(self):
        if self.request.method.lower() == 'post':
            return [CommentRateThrottle()]
        return super().get_throttles()

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
            muted_by_user = set(request.user.muted_users.values_list('id', flat=True)) if hasattr(request.user, 'muted_users') else set()
            excluded = blocked_by_user.union(blocking_user).union(muted_by_user)
            if excluded:
                comments = comments.exclude(user_id__in=excluded)

        if request.query_params.get('page') or request.query_params.get('paginate') == 'true':
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(comments, request)
            serializer = ReviewCommentSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = ReviewCommentSerializer(comments[:100], many=True, context={'request': request})
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

        from users.models import NotificationType
        from users.policies import can_view_review

        if not request.user.is_authenticated:
            return Response({'detail': 'Autenticación requerida.'}, status=status.HTTP_401_UNAUTHORIZED)

        if getattr(request.user, 'is_disciplinary_muted', False):
            return Response(
                {'detail': f"Tu cuenta se encuentra silenciada temporalmente por moderación hasta {request.user.muted_until}."},
                status=status.HTTP_403_FORBIDDEN,
            )

        review = get_object_or_404(Review.objects.select_related('user', 'book'), id=review_id)
        if (
            review.user.blocked_users.filter(id=request.user.id).exists()
            or request.user.blocked_users.filter(id=review.user_id).exists()
        ):
            return Response({'detail': 'No puedes interactuar con esta reseña.'}, status=status.HTTP_403_FORBIDDEN)

        if not can_view_review(request.user, review):
            raise PermissionDenied('No tienes permiso para ver esta reseña.')

        from mybookconnect.html_sanitizer import sanitize_plain_text

        raw_content = (request.data.get('content') or '').strip()
        content = sanitize_plain_text(raw_content)
        if not content:
            return Response({'detail': 'El comentario no puede estar vacío.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(content) > 1000:
            return Response({'detail': 'El comentario excede el máximo permitido (1000 caracteres).'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            comment = ReviewComment.objects.create(
                user=request.user,
                review=review,
                content=content,
            )

            from users.models import NotificationType
            from users.notification_service import NotificationService

            parent_id = request.data.get('parent_id') or request.data.get('parent')
            parent_comment = None
            if parent_id:
                parent_comment = ReviewComment.objects.filter(id=parent_id, review=review).first()

            if parent_comment and parent_comment.user_id != request.user.id:
                NotificationService.send_notification(
                    recipient=parent_comment.user,
                    actor=request.user,
                    notif_type=NotificationType.REPLY,
                    title=f"{request.user.username} respondió a tu comentario",
                    message=content[:120],
                    link=f"/books/{review.book_id}?review={review.id}",
                )
            elif review.user_id != request.user.id:
                NotificationService.send_notification(
                    recipient=review.user,
                    actor=request.user,
                    notif_type=NotificationType.COMMENT,
                    title=f"{request.user.username} comentó en tu reseña",
                    message=content[:120],
                    link=f"/books/{review.book_id}?review={review.id}",
                )

            try:
                from users.activity_service import record_activity
                from users.models import ActivityType
                record_activity(
                    user=request.user,
                    activity_type=ActivityType.COMMENT_ADDED,
                    book=review.book,
                    review=review,
                    target_user=review.user,
                    metadata={'comment_id': comment.id, 'review_id': review.id},
                )
            except Exception:
                pass

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

        with transaction.atomic():
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
    @idempotent(required=False)
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
            if version_param == 'v3':
                strategy = 'v3'
            elif version_param == 'v2':
                strategy = 'v2'
            elif version_param == 'v1':
                strategy = 'v1'
            else:
                strategy = 'hybrid'
        else:
            strategy = strategy.lower().strip()

        if strategy not in ('v1', 'canonical_v1', 'v2', 'collab', 'collaborative', 'v3', 'semantic_v3', 'vector', 'hybrid', 'rules', 'social', 'semantic'):
            strategy = 'v3' if version_param == 'v3' else ('v2' if version_param == 'v2' else 'v1')

        results = services.get_user_recommendations(
            user=request.user,
            limit=limit,
            strategy=strategy,
            request=request,
        )
        if strategy in ('v3', 'semantic_v3', 'vector') or version_param == 'v3':
            algo_version = 'v3'
        elif strategy in ('v2', 'collab', 'collaborative') or version_param == 'v2':
            algo_version = 'v2'
        else:
            algo_version = 'v1'

        return Response({
            'count': len(results),
            'strategy': strategy,
            'algorithm_version': algo_version,
            'results': results,
        })


class UserPreferenceEmbeddingView(APIView):
    """
    Endpoint para auditar el vector sintético de preferencias semánticas del usuario (v3).
    Representa el centroide ponderado de los libros leídos, calificados y terminados.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Vector de preferencias semánticas del usuario (v3)",
        description="Devuelve información de dimensionalidad, norma y componentes del embedding sintético del usuario.",
        responses={200: inline_serializer(
            name='UserPreferenceEmbeddingResponse',
            fields={
                'user_id': serializers.IntegerField(),
                'has_embedding': serializers.BooleanField(),
                'dimensions': serializers.IntegerField(),
                'books_used': serializers.IntegerField(),
                'weights_sum': serializers.FloatField(),
                'sample_components': serializers.ListField(child=serializers.FloatField()),
            },
        )},
        tags=['Books'],
    )
    def get(self, request):
        pref = services.get_user_preference_vector(user=request.user)
        data = pref.to_dict() if hasattr(pref, 'to_dict') else dict(pref)
        data['user_id'] = request.user.id
        return Response(data)


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


class BookRecommendationExplainView(APIView):
    """
    Endpoint para obtener la explicación estructurada multi-señal que justifica
    por qué se recomienda un libro específico al usuario autenticado (Fase 52).
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Explicación detallada de recomendación de libro",
        description="Devuelve el titular ('headline'), viñetas de evidencia (género, autor, semántica, social, colaborativa) y motivo principal.",
        parameters=[
            OpenApiParameter(
                name='version',
                type=str,
                location=OpenApiParameter.QUERY,
                required=False,
                default='v3',
                description="Versión del motor de recomendaciones para contextualizar la explicación ('v1', 'v2', 'v3').",
            ),
        ],
        responses={200: inline_serializer(
            name='RecommendationExplainResponse',
            fields={
                'book_id': serializers.IntegerField(),
                'book_title': serializers.CharField(),
                'headline': serializers.CharField(),
                'primary_reason': serializers.CharField(),
                'total_signals': serializers.IntegerField(),
                'algorithm_version': serializers.CharField(),
                'reasons': serializers.ListField(child=serializers.DictField()),
            },
        )},
        tags=['Books'],
    )
    def get(self, request, book_id):
        book = get_object_or_404(Book, pk=book_id)
        version = request.query_params.get('version', 'v3')
        explanation = services.explain_recommendation(
            user=request.user,
            book=book,
            algorithm_version=version,
        )
        explanation['book_id'] = book.id
        explanation['book_title'] = book.title
        return Response(explanation)


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
    @idempotent(required=False)
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


class ExternalSyncView(APIView):
    """
    Endpoint para sincronización externa bajo demanda de catálogo o libros (Fase 62).
    Soporta sincronización por ISBN, título o autor consultando Google Books / OpenLibrary.
    Protegido con @idempotent para prevenir duplicación o llamadas externas redundantes.
    """
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary="Sincronización externa de libros bajo demanda",
        description="Sincroniza metadatos y libros externos de forma idempotente.",
        request=inline_serializer(
            name='ExternalSyncRequest',
            fields={
                'isbn': serializers.CharField(required=False),
                'title': serializers.CharField(required=False),
                'author': serializers.CharField(required=False),
            },
        ),
        responses={
            200: inline_serializer(
                name='ExternalSyncResponse',
                fields={'synced': serializers.BooleanField(), 'detail': serializers.CharField(), 'count': serializers.IntegerField(required=False)},
            ),
            400: OpenApiResponse(description="Parámetros insuficientes"),
        },
        tags=['Books'],
    )
    @idempotent(required=False)
    def post(self, request):
        query_isbn = (request.data.get('isbn') or '').strip()
        query_title = (request.data.get('title') or '').strip()
        author_name = (request.data.get('author') or '').strip()

        if not query_isbn and not query_title and not author_name:
            return Response({'detail': 'Debe indicar al menos isbn, title o author para sincronizar.'}, status=400)

        if query_isbn:
            book = services.import_single_by_query(query_isbn=query_isbn)
            return Response({
                'synced': book is not None,
                'detail': f"Sincronización de ISBN {query_isbn} completada." if book else "No se encontraron datos externos para este ISBN.",
                'book_id': book.id if book else None,
            }, status=200)

        if author_name:
            count = services.import_books_by_author(author_name)
            return Response({
                'synced': True,
                'count': count,
                'detail': f"Se sincronizaron {count} libros para el autor {author_name}.",
            }, status=200)

        books = services.import_multiple_by_title(query_title, offset=0)
        return Response({
            'synced': bool(books),
            'count': len(books),
            'detail': f"Se encontraron y sincronizaron {len(books)} libros para el título {query_title}.",
        }, status=200)


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
    permission_classes = (permissions.AllowAny,)

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
        from rest_framework.exceptions import NotFound, PermissionDenied

        from users.policies import are_mutually_blocked, can_match
        UserModel = get_user_model()
        target_user = get_object_or_404(UserModel, id=user_id)

        if target_user == request.user:
            return Response({'match_percentage': 100, 'is_self': True, 'common_books': []})

        if are_mutually_blocked(request.user, target_user):
            raise NotFound("Usuario no encontrado.")
        if not can_match(request.user, target_user):
            raise PermissionDenied("La biblioteca de este usuario es privada.")

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
            'items__book', 'items__book__author', 'items__added_by', 'followers', 'collaborators__user'
        )

        user_id_param = self.request.query_params.get('user_id')
        if user_id_param:
            queryset = queryset.filter(user_id=user_id_param)

        if self.request.query_params.get('collaborative') == 'true' and user.is_authenticated:
            return queryset.filter(
                Q(collaborators__user=user, collaborators__status__in=['ACCEPTED', 'PENDING']) |
                Q(user=user, is_collaborative=True)
            ).distinct()

        if self.request.query_params.get('my_lists') == 'true' and user.is_authenticated:
            return queryset.filter(user=user)

        if self.request.query_params.get('followed') == 'true' and user.is_authenticated:
            return queryset.filter(followers__user=user)

        from users.policies import filter_visible_reading_lists
        return filter_visible_reading_lists(user, queryset)

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return ReadingListCreateUpdateSerializer
        return ReadingListSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Registrar incremento de apertura si el consultante no es el dueño
        if request.user != instance.user:
            ReadingList.objects.filter(pk=instance.pk).update(views_count=F('views_count') + 1)
            instance.views_count += 1
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        with transaction.atomic():
            instance = serializer.save(user=self.request.user)
            if instance.privacy != ReadingListPrivacy.PRIVATE:
                try:
                    from users.activity_service import record_activity
                    from users.models import ActivityType
                    record_activity(
                        user=self.request.user,
                        activity_type=ActivityType.LIST_CREATED,
                        metadata={'list_id': instance.id, 'name': instance.name, 'privacy': instance.privacy},
                    )
                except Exception:
                    pass

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.user != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo el creador puede editar esta lista.")
        with transaction.atomic():
            serializer.save()

    def perform_destroy(self, instance):
        if instance.user != self.request.user and not self.request.user.is_staff:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Solo el creador puede eliminar esta lista.")
        with transaction.atomic():
            instance.delete()

    @action(detail=True, methods=['post'], url_path='add-book', permission_classes=[permissions.IsAuthenticated])
    def add_book(self, request, pk=None):
        """Añade un libro a la lista en una posición específica o al final bajo bloqueo exclusivo de fila."""
        reading_list = self.get_object()
        user = request.user

        is_owner = (reading_list.user == user)
        is_staff = user.is_staff
        can_add = is_owner or is_staff
        if not can_add and reading_list.is_collaborative:
            collab = reading_list.collaborators.filter(user=user, status='ACCEPTED').first()
            if collab and collab.can_add_books:
                can_add = True

        if not can_add:
            return Response({'detail': 'No tienes permiso para modificar esta lista.'}, status=status.HTTP_403_FORBIDDEN)

        book_id = request.data.get('book_id')
        if not book_id:
            return Response({'detail': 'El campo book_id es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        book = get_object_or_404(Book, id=book_id)
        position_req = request.data.get('position')
        notes = request.data.get('notes', '')

        with transaction.atomic():
            # Bloquear la lista padre para serializar adiciones concurrentes y cómputo de posiciones
            locked_list = ReadingList.objects.select_for_update().get(pk=reading_list.pk)

            if ReadingListItem.objects.filter(reading_list=locked_list, book=book).exists():
                return Response({'detail': 'Este libro ya se encuentra en la lista.'}, status=status.HTTP_400_BAD_REQUEST)

            if position_req is None:
                from django.db.models import Max
                max_pos = ReadingListItem.objects.filter(reading_list=locked_list).aggregate(m=Max('position'))['m'] or 0
                position = max_pos + 1
            else:
                try:
                    position = int(position_req)
                except (ValueError, TypeError):
                    position = 1

            try:
                with transaction.atomic():
                    item = ReadingListItem.objects.create(
                        reading_list=locked_list,
                        book=book,
                        position=position,
                        notes=notes,
                        added_by=user,
                    )
            except IntegrityError:
                return Response({'detail': 'Este libro ya se encuentra en la lista.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ReadingListItemSerializer(item, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['delete', 'post'], url_path='remove-book', permission_classes=[permissions.IsAuthenticated])
    def remove_book(self, request, pk=None):
        """Elimina un libro de la lista de lectura."""
        reading_list = self.get_object()
        user = request.user

        book_id = request.data.get('book_id') or request.query_params.get('book_id')
        if not book_id:
            return Response({'detail': 'El parámetro book_id es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        item = ReadingListItem.objects.filter(reading_list=reading_list, book_id=book_id).first()
        if not item:
            return Response({'detail': 'El libro no estaba en esta lista.'}, status=status.HTTP_404_NOT_FOUND)

        can_remove = False
        if reading_list.user == user or user.is_staff:
            can_remove = True
        elif reading_list.is_collaborative:
            collab = reading_list.collaborators.filter(user=user, status='ACCEPTED').first()
            if collab:
                if collab.can_remove_books or item.added_by_id == user.id:
                    can_remove = True

        if not can_remove:
            return Response({'detail': 'No tienes permiso para modificar esta lista.'}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            item.delete()

        return Response({'detail': 'Libro eliminado de la lista.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['put', 'post'], url_path='reorder', permission_classes=[permissions.IsAuthenticated])
    def reorder(self, request, pk=None):
        """
        Reordena los libros de la lista bajo bloqueo exclusivo de fila. Acepta:
        [ {"book_id": 1, "position": 1}, {"book_id": 2, "position": 2} ] o [1, 2, 3] (lista ordenada de IDs).
        """
        reading_list = self.get_object()
        user = request.user

        can_edit = (reading_list.user == user or user.is_staff)
        if not can_edit and reading_list.is_collaborative:
            can_edit = reading_list.collaborators.filter(user=user, status='ACCEPTED').exists()

        if not can_edit:
            return Response({'detail': 'No tienes permiso para modificar esta lista.'}, status=status.HTTP_403_FORBIDDEN)

        orders = request.data.get('items') or request.data
        if not isinstance(orders, list):
            return Response({'detail': 'Se espera una lista de elementos para reordenar.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            locked_list = ReadingList.objects.select_for_update().get(pk=reading_list.pk)
            for idx, entry in enumerate(orders, start=1):
                if isinstance(entry, dict):
                    b_id = entry.get('book_id') or entry.get('id')
                    pos = entry.get('position', idx)
                else:
                    b_id = entry
                    pos = idx

                ReadingListItem.objects.filter(reading_list=locked_list, book_id=b_id).update(position=pos)

        updated_list = ReadingList.objects.prefetch_related('items__book', 'items__book__author').get(pk=reading_list.pk)
        return Response(ReadingListSerializer(updated_list, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='follow', permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, pk=None):
        """Sigue una lista de lectura pública."""
        reading_list = self.get_object()
        if reading_list.user == request.user:
            return Response({'detail': 'No puedes seguir tu propia lista.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            follow_obj, created = ReadingListFollow.objects.get_or_create(
                user=request.user,
                reading_list=reading_list,
            )
            if created and reading_list.user_id != request.user.id:
                from users.models import NotificationType
                from users.notification_service import NotificationService

                NotificationService.send_notification(
                    recipient=reading_list.user,
                    actor=request.user,
                    notif_type=NotificationType.LIST_FOLLOW,
                    title='Nuevo seguidor en tu lista',
                    message=f"{request.user.username} ha comenzado a seguir tu lista '{reading_list.name}'.",
                    link=f"/reading-lists?id={reading_list.id}",
                )
        return Response({'detail': 'Ahora sigues esta lista.', 'created': created}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete', 'post'], url_path='unfollow', permission_classes=[permissions.IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Deja de seguir una lista de lectura."""
        reading_list = self.get_object()
        with transaction.atomic():
            deleted_count, _ = ReadingListFollow.objects.filter(
                user=request.user,
                reading_list=reading_list,
            ).delete()
        return Response({'detail': 'Has dejado de seguir esta lista.', 'deleted': deleted_count > 0}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='clone', permission_classes=[permissions.IsAuthenticated])
    def clone(self, request, pk=None):
        """Clona una lista pública o accesible en la biblioteca del usuario actual (Fase 21)."""
        source_list = self.get_object()
        with transaction.atomic():
            new_list = ReadingList.objects.create(
                user=request.user,
                name=f"Copia de {source_list.name}"[:200],
                description=source_list.description,
                privacy=ReadingListPrivacy.PRIVATE,
            )
            items_to_create = [
                ReadingListItem(
                    reading_list=new_list,
                    book=item.book,
                    position=item.position,
                    notes=item.notes,
                )
                for item in source_list.items.all()
            ]
            if items_to_create:
                ReadingListItem.objects.bulk_create(items_to_create)

            if source_list.user_id != request.user.id:
                from users.models import NotificationType
                from users.notification_service import NotificationService

                NotificationService.send_notification(
                    recipient=source_list.user,
                    actor=request.user,
                    notif_type=NotificationType.LIST_FOLLOW,
                    title='Alguien ha guardado tu lista',
                    message=f"{request.user.username} ha guardado una copia de tu lista '{source_list.name}'.",
                    link=f"/reading-lists?id={source_list.id}",
                )

        serializer = self.get_serializer(new_list)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, pk=None):
        """Consulta o añade comentarios sobre la lista de lectura (Fase 21)."""
        reading_list = self.get_object()

        if request.method == 'GET':
            comments_qs = reading_list.comments.filter(
                deleted_at__isnull=True, is_moderated=False
            ).select_related('user')
            serializer = ReadingListCommentSerializer(comments_qs, many=True, context={'request': request})
            return Response(serializer.data)

        # POST: crear comentario
        if not request.user.is_authenticated:
            return Response({'detail': 'Autenticación requerida para comentar.'}, status=status.HTTP_401_UNAUTHORIZED)

        raw_content = request.data.get('content', '')
        if not isinstance(raw_content, str) or not raw_content.strip():
            return Response({'detail': 'El contenido del comentario es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        clean_content = sanitize_plain_text(raw_content).strip()
        with transaction.atomic():
            comment = ReadingListComment.objects.create(
                user=request.user,
                reading_list=reading_list,
                content=clean_content,
            )
            if reading_list.user_id != request.user.id:
                from users.models import NotificationType
                from users.notification_service import NotificationService

                NotificationService.send_notification(
                    recipient=reading_list.user,
                    actor=request.user,
                    notif_type=NotificationType.COMMENT,
                    title=f"{request.user.username} comentó en tu lista",
                    message=f"Nuevo comentario en '{reading_list.name}': {clean_content[:100]}",
                    link=f"/reading-lists?id={reading_list.id}",
                )
        return Response(
            ReadingListCommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=['delete'],
        url_path=r'comments/(?P<comment_id>[^/.]+)',
        permission_classes=[permissions.IsAuthenticated],
    )
    def delete_comment(self, request, pk=None, comment_id=None):
        """Elimina un comentario propio o por parte del staff (soft delete)."""
        reading_list = self.get_object()
        comment = get_object_or_404(
            reading_list.comments.filter(deleted_at__isnull=True), id=comment_id
        )
        if comment.user != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'No tienes permiso para eliminar este comentario.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        comment.delete()
        return Response({'detail': 'Comentario eliminado.'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'], url_path='collaborators', permission_classes=[permissions.IsAuthenticated])
    def collaborators(self, request, pk=None):
        """Lista o invita colaboradores a una lista de lectura."""
        reading_list = self.get_object()

        if request.method == 'GET':
            collaborators_qs = reading_list.collaborators.select_related('user', 'invited_by').order_by('created_at')
            serializer = ReadingListCollaboratorSerializer(collaborators_qs, many=True, context={'request': request})
            return Response(serializer.data)

        # POST: invitar colaborador
        if reading_list.user != request.user and not request.user.is_staff:
            return Response({'detail': 'Solo el creador de la lista puede invitar colaboradores.'}, status=status.HTTP_403_FORBIDDEN)

        from django.contrib.auth import get_user_model
        UserModel = get_user_model()

        user_id = request.data.get('user_id')
        username = request.data.get('username')
        email = request.data.get('email')

        target_user = None
        if user_id:
            target_user = UserModel.objects.filter(id=user_id).first()
        elif username:
            target_user = UserModel.objects.filter(username__iexact=username).first()
        elif email:
            target_user = UserModel.objects.filter(email__iexact=email).first()

        if not target_user:
            return Response({'detail': 'Usuario a invitar no encontrado.'}, status=status.HTTP_404_NOT_FOUND)

        if target_user == reading_list.user:
            return Response({'detail': 'El creador de la lista ya es el propietario.'}, status=status.HTTP_400_BAD_REQUEST)

        if reading_list.collaborators.filter(user=target_user).exists():
            return Response({'detail': 'Este usuario ya ha sido invitado a la lista.'}, status=status.HTTP_400_BAD_REQUEST)

        role = request.data.get('role', 'EDITOR')
        can_add_books = request.data.get('can_add_books', True)
        can_remove_books = request.data.get('can_remove_books', False)

        with transaction.atomic():
            if not reading_list.is_collaborative:
                reading_list.is_collaborative = True
                reading_list.save(update_fields=['is_collaborative'])

            collaborator = ReadingListCollaborator.objects.create(
                reading_list=reading_list,
                user=target_user,
                invited_by=request.user,
                role=role,
                status='PENDING',
                can_add_books=can_add_books,
                can_remove_books=can_remove_books,
            )

            try:
                from users.models import NotificationType
                from users.notification_service import NotificationService
                NotificationService.send_notification(
                    recipient=target_user,
                    actor=request.user,
                    notif_type=NotificationType.LIST_FOLLOW,
                    title='Invitación a lista colaborativa',
                    message=f"{request.user.username} te ha invitado a colaborar en la lista '{reading_list.name}'.",
                    link=f"/reading-lists?id={reading_list.id}",
                )
            except Exception:
                pass

        return Response(
            ReadingListCollaboratorSerializer(collaborator, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['patch', 'delete'], url_path=r'collaborators/(?P<user_id>\d+)', permission_classes=[permissions.IsAuthenticated])
    def manage_collaborator(self, request, pk=None, user_id=None):
        """Gestiona el estado o permisos de un colaborador (aceptar/rechazar/editar/eliminar)."""
        reading_list = self.get_object()
        collaborator = get_object_or_404(reading_list.collaborators.select_related('user'), user_id=user_id)

        is_self = (request.user.id == collaborator.user_id)
        is_owner = (reading_list.user == request.user or request.user.is_staff)

        if request.method == 'PATCH':
            new_status = request.data.get('status')
            with transaction.atomic():
                if is_self:
                    if new_status in ['ACCEPTED', 'REJECTED']:
                        collaborator.status = new_status
                        collaborator.save(update_fields=['status', 'updated_at'])
                        return Response(ReadingListCollaboratorSerializer(collaborator, context={'request': request}).data)
                    return Response({'detail': 'Estado no válido.'}, status=status.HTTP_400_BAD_REQUEST)

                if is_owner:
                    if new_status in ['ACCEPTED', 'REJECTED', 'PENDING']:
                        collaborator.status = new_status
                    if 'can_add_books' in request.data:
                        collaborator.can_add_books = bool(request.data['can_add_books'])
                    if 'can_remove_books' in request.data:
                        collaborator.can_remove_books = bool(request.data['can_remove_books'])
                    if 'role' in request.data and request.data['role'] in ['EDITOR', 'VIEWER']:
                        collaborator.role = request.data['role']
                    collaborator.save()
                    return Response(ReadingListCollaboratorSerializer(collaborator, context={'request': request}).data)

                return Response({'detail': 'No tienes permiso para modificar este colaborador.'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'DELETE':
            if not is_self and not is_owner:
                return Response({'detail': 'No tienes permiso para eliminar este colaborador.'}, status=status.HTTP_403_FORBIDDEN)
            with transaction.atomic():
                collaborator.delete()
            return Response({'detail': 'Colaborador eliminado.'}, status=status.HTTP_200_OK)


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


# ==============================================================================
# Vistas de Monetización, Afiliados y Plataforma de Autores (Fase 31 — RoadmapV2)
# ==============================================================================

class BookAffiliateLinksView(APIView):
    """
    Entrega enlaces canónicos de compra en Amazon para el libro en sus diferentes formatos
    (libro físico, ebook Kindle, audiolibro Audible) junto con la declaración legal de afiliado.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        book = get_object_or_404(Book.objects.select_related('author'), pk=pk)
        from .services.affiliate_service import AffiliateService
        data = AffiliateService.generate_affiliate_links(book)
        return Response(data, status=status.HTTP_200_OK)


class BookAffiliateClickView(APIView):
    """
    Registra un clic de afiliado anonimizado para telemetría y conversión.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        book = get_object_or_404(Book, pk=pk)
        format_type = request.data.get('format', 'paperback')
        from .services.affiliate_service import AffiliateService
        click = AffiliateService.record_click(book, format_type)
        return Response(
            {'status': 'recorded', 'click_id': click.id, 'format': click.format},
            status=status.HTTP_201_CREATED,
        )


class AuthorProfileMeView(APIView):
    """
    Consulta y actualización del perfil de autor del usuario autenticado.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .serializers import AuthorProfileSerializer
        from .services.author_service import AuthorService
        profile = AuthorService.get_or_create_profile(request.user)
        serializer = AuthorProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        from .serializers import AuthorProfileSerializer
        from .services.author_service import AuthorService
        profile = AuthorService.get_or_create_profile(request.user)
        for field in ('pen_name', 'bio', 'website', 'twitter', 'instagram'):
            if field in request.data:
                setattr(profile, field, request.data[field])
        profile.save()
        serializer = AuthorProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorClaimView(APIView):
    """
    Permite a un usuario solicitar la verificación o reclamo de un autor del catálogo.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        author_id = request.data.get('author_id')
        if not author_id:
            return Response({'detail': 'El campo author_id es obligatorio.'}, status=status.HTTP_400_BAD_REQUEST)

        pen_name = request.data.get('pen_name', '')
        verification_notes = request.data.get('verification_notes', '')

        from .serializers import AuthorProfileSerializer
        from .services.author_service import AuthorService
        try:
            profile = AuthorService.claim_author(
                user=request.user,
                author_id=int(author_id),
                pen_name=pen_name,
                verification_notes=verification_notes,
            )
            serializer = AuthorProfileSerializer(profile, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ValueError as err:
            return Response({'detail': str(err)}, status=status.HTTP_400_BAD_REQUEST)


class AuthorDashboardView(APIView):
    """
    Panel analítico privado con métricas consolidadas de las obras del autor.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .services.author_service import AuthorService
        profile = AuthorService.get_or_create_profile(request.user)
        metrics = AuthorService.get_author_dashboard_metrics(profile)
        return Response(metrics, status=status.HTTP_200_OK)


class AuthorAnnouncementCreateView(APIView):
    """
    Publicación de comunicados y publicaciones avanzadas por parte de un autor.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from .serializers import AuthorAnnouncementSerializer
        from .services.author_service import AuthorService

        profile = AuthorService.get_or_create_profile(request.user)
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        book_id = request.data.get('book_id')
        is_pinned = bool(request.data.get('is_pinned', False))
        publication_type = request.data.get('publication_type', 'ANNOUNCEMENT')
        excerpt = request.data.get('excerpt', '').strip()
        has_spoilers = bool(request.data.get('has_spoilers', False))
        spoiler_warning = request.data.get('spoiler_warning', '').strip()
        estimated_reading_time = request.data.get('estimated_reading_time')
        is_draft = bool(request.data.get('is_draft', False))
        author_id = request.data.get('author_id') or request.data.get('author')

        if not title or not content:
            return Response(
                {'detail': 'Título y contenido son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        announcement = AuthorService.create_announcement(
            author_profile=profile,
            title=title,
            content=content,
            book_id=int(book_id) if book_id else None,
            is_pinned=is_pinned,
            publication_type=publication_type,
            excerpt=excerpt,
            has_spoilers=has_spoilers,
            spoiler_warning=spoiler_warning,
            estimated_reading_time=int(estimated_reading_time) if estimated_reading_time else None,
            is_draft=is_draft,
            author_id=int(author_id) if author_id else None,
        )
        serializer = AuthorAnnouncementSerializer(announcement, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AuthorAnnouncementListView(APIView):
    """
    Listado público de comunicados y publicaciones avanzadas para un autor del catálogo.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        from .serializers import AuthorAnnouncementSerializer
        from .services.author_service import AuthorService

        include_drafts = False
        if request.user.is_authenticated and request.query_params.get('drafts') == 'true':
            include_drafts = True

        pub_type = request.query_params.get('type') or request.query_params.get('publication_type')
        announcements = AuthorService.get_announcements_for_author(
            author_id=pk,
            include_drafts=include_drafts,
            publication_type=pub_type,
        )
        serializer = AuthorAnnouncementSerializer(announcements, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorClaimCreateView(APIView):
    """
    Permite a un usuario autenticado reclamar la página de un autor del catálogo.
    RoadmapV3 Sprint 3 (Sección 4.4).
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Reclamar página de autor",
        tags=['Authors'],
    )
    def post(self, request, pk):
        from django.shortcuts import get_object_or_404
        from .models import Author
        from .serializers import AuthorClaimCreateSerializer, AuthorClaimAdminSerializer

        author = get_object_or_404(Author, id=pk)
        serializer = AuthorClaimCreateSerializer(
            data=request.data,
            context={'author': author, 'user': request.user, 'request': request},
        )
        serializer.is_valid(raise_exception=True)
        claim = serializer.save()
        return Response(
            AuthorClaimAdminSerializer(claim, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class AuthorClaimStatusView(APIView):
    """
    Comprueba si el usuario autenticado tiene reclamaciones para este autor.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Consultar estado de reclamación del autor para el usuario actual",
        tags=['Authors'],
    )
    def get(self, request, pk):
        from django.shortcuts import get_object_or_404
        from .models import Author, AuthorClaim, AuthorClaimStatus

        author = get_object_or_404(Author, id=pk)
        latest_claim = AuthorClaim.objects.filter(
            author=author,
            user=request.user,
        ).order_by('-created_at').first()

        is_owner = (author.claimed_by_id == request.user.id)
        has_pending = (latest_claim.status == AuthorClaimStatus.PENDING) if latest_claim else False

        return Response({
            'author_id': author.id,
            'is_verified': author.is_verified,
            'is_owner': is_owner,
            'has_pending_claim': has_pending,
            'claim_status': latest_claim.status if latest_claim else None,
            'claim_id': latest_claim.id if latest_claim else None,
        }, status=status.HTTP_200_OK)


class PublicFAQListView(generics.ListAPIView):
    """
    Listado público de Preguntas Frecuentes (FAQs) activas para visualización en formato acordeón.
    RoadmapV3 Sprint 3.
    """
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        from .serializers import FAQSerializer
        return FAQSerializer

    def get_queryset(self):
        from .models import FAQ
        qs = FAQ.objects.filter(is_published=True).order_by('order', 'id')
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category.lower().strip())
        return qs


class AuthorEventViewSet(viewsets.ModelViewSet):
    """
    Gestión y consulta de eventos literarios de autores (presentaciones, firmas, Q&A, etc.).
    RoadmapV3 Sección 30 — Sprint 11.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        from .models import AuthorEvent
        qs = AuthorEvent.objects.select_related('author', 'book', 'created_by', 'author_profile').prefetch_related('attendees')

        author_id = self.request.query_params.get('author') or self.request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(author_id=author_id)

        book_id = self.request.query_params.get('book') or self.request.query_params.get('book_id')
        if book_id:
            qs = qs.filter(book_id=book_id)

        event_type = self.request.query_params.get('event_type')
        if event_type:
            qs = qs.filter(event_type=event_type)

        event_format = self.request.query_params.get('format') or self.request.query_params.get('event_format')
        if event_format:
            qs = qs.filter(event_format=event_format)

        upcoming = self.request.query_params.get('upcoming')
        if upcoming in ('true', '1', 'True'):
            from django.utils import timezone
            qs = qs.filter(start_time__gte=timezone.now(), is_cancelled=False)
        elif self.request.query_params.get('past') in ('true', '1', 'True'):
            from django.utils import timezone
            qs = qs.filter(start_time__lt=timezone.now())

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search) | Q(location_name__icontains=search))

        return qs.order_by('start_time')

    def get_serializer_class(self):
        from .serializers import AuthorEventCreateUpdateSerializer, AuthorEventSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorEventCreateUpdateSerializer
        return AuthorEventSerializer

    def perform_create(self, serializer):
        from .models import AuthorProfile
        author = serializer.validated_data['author']
        author_profile = AuthorProfile.objects.filter(user=self.request.user, author=author).first()
        serializer.save(created_by=self.request.user, author_profile=author_profile)

    def perform_destroy(self, instance):
        user = self.request.user
        is_owner = (instance.created_by_id == user.id or instance.author.claimed_by_id == user.id)
        is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_owner or is_staff):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para eliminar este evento.")
        instance.delete()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        is_owner = (instance.created_by_id == user.id or instance.author.claimed_by_id == user.id)
        is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        if not (is_owner or is_staff):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para modificar este evento.")
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, pk=None):
        from .models import AuthorEventAttendee
        event = self.get_object()

        if event.is_cancelled:
            return Response({'detail': 'Este evento ha sido cancelado.'}, status=status.HTTP_400_BAD_REQUEST)

        notes = request.data.get('notes', '').strip()
        attendee = AuthorEventAttendee.objects.filter(event=event, user=request.user).first()

        if attendee:
            if attendee.status in (AuthorEventAttendee.AttendeeStatus.REGISTERED, AuthorEventAttendee.AttendeeStatus.WAITLIST):
                if notes:
                    attendee.notes = notes
                    attendee.save()
                return Response({
                    'detail': f'Ya estás inscrito en este evento ({attendee.get_status_display()}).',
                    'status': attendee.status,
                    'is_waitlist': (attendee.status == AuthorEventAttendee.AttendeeStatus.WAITLIST),
                }, status=status.HTTP_200_OK)
            else:
                # Was CANCELLED, reactivate
                new_status = AuthorEventAttendee.AttendeeStatus.WAITLIST if event.is_full else AuthorEventAttendee.AttendeeStatus.REGISTERED
                attendee.status = new_status
                attendee.notes = notes
                attendee.save()
                return Response({
                    'detail': f'Inscripción reactivada ({attendee.get_status_display()}).',
                    'status': attendee.status,
                    'is_waitlist': (new_status == AuthorEventAttendee.AttendeeStatus.WAITLIST),
                }, status=status.HTTP_200_OK)

        new_status = AuthorEventAttendee.AttendeeStatus.WAITLIST if event.is_full else AuthorEventAttendee.AttendeeStatus.REGISTERED
        attendee = AuthorEventAttendee.objects.create(
            event=event,
            user=request.user,
            status=new_status,
            notes=notes,
        )
        msg = 'Te hemos añadido a la lista de espera.' if new_status == AuthorEventAttendee.AttendeeStatus.WAITLIST else '¡Inscripción confirmada!'
        return Response({
            'detail': msg,
            'status': new_status,
            'is_waitlist': (new_status == AuthorEventAttendee.AttendeeStatus.WAITLIST),
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def cancel_registration(self, request, pk=None):
        from .models import AuthorEventAttendee
        event = self.get_object()
        attendee = AuthorEventAttendee.objects.filter(event=event, user=request.user).first()

        if not attendee or attendee.status == AuthorEventAttendee.AttendeeStatus.CANCELLED:
            return Response({'detail': 'No tienes una inscripción activa para este evento.'}, status=status.HTTP_400_BAD_REQUEST)

        was_registered = (attendee.status == AuthorEventAttendee.AttendeeStatus.REGISTERED)
        attendee.status = AuthorEventAttendee.AttendeeStatus.CANCELLED
        attendee.save()

        # If user had a confirmed seat, promote next person on waitlist
        promoted_username = None
        if was_registered:
            next_in_line = event.attendees.filter(
                status=AuthorEventAttendee.AttendeeStatus.WAITLIST
            ).order_by('created_at').first()
            if next_in_line:
                next_in_line.status = AuthorEventAttendee.AttendeeStatus.REGISTERED
                next_in_line.save()
                promoted_username = next_in_line.user.username

        return Response({
            'detail': 'Tu inscripción ha sido cancelada correctamente.',
            'status': 'CANCELLED',
            'promoted_user': promoted_username,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def attendees(self, request, pk=None):
        from .serializers import AuthorEventAttendeeSerializer
        event = self.get_object()
        user = request.user
        is_organizer = (event.created_by_id == user.id or event.author.claimed_by_id == user.id or user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR'))

        if is_organizer:
            attendees = event.attendees.select_related('user').all().order_by('created_at')
        else:
            attendees = event.attendees.filter(status='REGISTERED').select_related('user').order_by('created_at')

        serializer = AuthorEventAttendeeSerializer(attendees, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorPublicationViewSet(viewsets.ModelViewSet):
    """
    Gestión CRUD completa y consulta de publicaciones avanzadas de autor (adelantos, notas, comunicados).
    RoadmapV3 Sección 30 — Sprint 12.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        from .serializers import AuthorAnnouncementCreateUpdateSerializer, AuthorAnnouncementSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorAnnouncementCreateUpdateSerializer
        return AuthorAnnouncementSerializer

    def get_queryset(self):
        from django.db.models import Q
        from .models import AuthorAnnouncement
        qs = AuthorAnnouncement.objects.select_related('author_profile', 'author', 'book')

        author_id = self.request.query_params.get('author') or self.request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(Q(author_id=author_id) | Q(author_profile__author_id=author_id))

        book_id = self.request.query_params.get('book') or self.request.query_params.get('book_id')
        if book_id:
            qs = qs.filter(book_id=book_id)

        pub_type = self.request.query_params.get('type') or self.request.query_params.get('publication_type')
        if pub_type:
            qs = qs.filter(publication_type=pub_type)

        is_pinned = self.request.query_params.get('pinned')
        if is_pinned in ('true', '1'):
            qs = qs.filter(is_pinned=True)

        user = self.request.user
        drafts_param = self.request.query_params.get('drafts')
        if drafts_param in ('true', '1') and user.is_authenticated:
            qs = qs.filter(Q(is_draft=False) | Q(author_profile__user=user) | Q(author__claimed_by=user))
        else:
            qs = qs.filter(is_draft=False)

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search) | Q(excerpt__icontains=search))

        return qs.order_by('-is_pinned', '-created_at')

    def perform_create(self, serializer):
        from .models import Author, AuthorProfile
        from .services.author_service import AuthorService
        user = self.request.user
        author = serializer.validated_data.get('author')
        profile = AuthorService.get_or_create_profile(user)

        if not author:
            if profile.author:
                author = profile.author
            elif Author.objects.filter(claimed_by=user).exists():
                author = Author.objects.filter(claimed_by=user).first()

        if author:
            is_owner = (
                author.claimed_by_id == user.id or
                (profile.author_id == author.id and profile.is_verified) or
                user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
            )
            if not is_owner:
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("No tienes permisos para publicar en nombre de este autor.")

        serializer.save(author_profile=profile, author=author)

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        is_owner = (
            instance.author_profile.user_id == user.id or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para modificar esta publicación.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        is_owner = (
            instance.author_profile.user_id == user.id or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para eliminar esta publicación.")
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def toggle_pin(self, request, pk=None):
        instance = self.get_object()
        user = request.user
        is_owner = (
            instance.author_profile.user_id == user.id or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            return Response({'detail': 'No tienes permisos.'}, status=status.HTTP_403_FORBIDDEN)
        instance.is_pinned = not instance.is_pinned
        instance.save()
        return Response({'id': instance.id, 'is_pinned': instance.is_pinned}, status=status.HTTP_200_OK)


class AuthorNewsletterViewSet(viewsets.ModelViewSet):
    """
    CRUD y gestión de newsletters/boletines literarios de autores, con suscripción 1-clic y consulta de suscriptores.
    """
    queryset = AuthorNewsletter.objects.select_related('author', 'author_profile').prefetch_related('subscribers', 'issues')
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorNewsletterCreateUpdateSerializer
        return AuthorNewsletterSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        author_id = self.request.query_params.get('author') or self.request.query_params.get('author_id')
        if author_id:
            qs = qs.filter(Q(author_id=author_id) | Q(author_profile__author_id=author_id))

        user = self.request.user
        if not user.is_staff and getattr(user, 'role', '') not in ('ADMIN', 'MODERATOR'):
            # Los usuarios no administradores solo ven newsletters activas o las propias
            if user.is_authenticated:
                qs = qs.filter(Q(is_active=True) | Q(author__claimed_by=user) | Q(author_profile__user=user))
            else:
                qs = qs.filter(is_active=True)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        from .models import AuthorProfile
        from .services.author_service import AuthorService
        user = self.request.user
        author = serializer.validated_data.get('author')
        profile = AuthorService.get_or_create_profile(user)
        if not author and profile.author:
            author = profile.author
        serializer.save(author=author, author_profile=profile)

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        is_owner = (
            (instance.author_profile and instance.author_profile.user_id == user.id) or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para modificar este boletín.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        is_owner = (
            (instance.author_profile and instance.author_profile.user_id == user.id) or
            (instance.author and instance.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para eliminar este boletín.")
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        newsletter = self.get_object()
        sub, created = AuthorNewsletterSubscriber.objects.get_or_create(
            newsletter=newsletter,
            user=request.user,
            defaults={'is_active': True}
        )
        if not created and not sub.is_active:
            sub.is_active = True
            sub.unsubscribed_at = None
            sub.save(update_fields=['is_active', 'unsubscribed_at'])

        return Response({
            'detail': 'Te has suscrito correctamente al boletín del autor.',
            'is_subscribed': True,
            'active_subscribers_count': newsletter.active_subscribers_count,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unsubscribe(self, request, pk=None):
        from django.utils import timezone
        newsletter = self.get_object()
        sub = AuthorNewsletterSubscriber.objects.filter(newsletter=newsletter, user=request.user).first()
        if sub and sub.is_active:
            sub.is_active = False
            sub.unsubscribed_at = timezone.now()
            sub.save(update_fields=['is_active', 'unsubscribed_at'])

        return Response({
            'detail': 'Te has desuscrito del boletín.',
            'is_subscribed': False,
            'active_subscribers_count': newsletter.active_subscribers_count,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_subscriptions(self, request):
        subs = AuthorNewsletterSubscriber.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('newsletter__author')
        newsletters = [sub.newsletter for sub in subs if sub.newsletter.is_active]
        serializer = AuthorNewsletterSerializer(newsletters, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def subscribers(self, request, pk=None):
        newsletter = self.get_object()
        user = request.user
        is_owner = (
            (newsletter.author_profile and newsletter.author_profile.user_id == user.id) or
            (newsletter.author and newsletter.author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            return Response({'detail': 'No tienes permisos para consultar la lista de suscriptores.'}, status=status.HTTP_403_FORBIDDEN)

        subs = newsletter.subscribers.filter(is_active=True).select_related('user').order_by('-subscribed_at')
        page = self.paginate_queryset(subs)
        if page is not None:
            serializer = AuthorNewsletterSubscriberSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = AuthorNewsletterSubscriberSerializer(subs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthorNewsletterIssueViewSet(viewsets.ModelViewSet):
    """
    Gestión de entregas de boletines (borradores, programados y enviados) y acción de envío inmediato.
    """
    queryset = AuthorNewsletterIssue.objects.select_related('newsletter__author')
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return AuthorNewsletterIssueCreateUpdateSerializer
        return AuthorNewsletterIssueSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        qs = super().get_queryset()
        newsletter_id = self.request.query_params.get('newsletter') or self.request.query_params.get('newsletter_id')
        if newsletter_id:
            qs = qs.filter(newsletter_id=newsletter_id)

        user = self.request.user
        # Si no es staff ni autor de la newsletter, solo puede ver entregas enviadas (SENT)
        if not user.is_staff and getattr(user, 'role', '') not in ('ADMIN', 'MODERATOR'):
            if user.is_authenticated:
                qs = qs.filter(
                    Q(status=AuthorNewsletterIssue.IssueStatus.SENT) |
                    Q(newsletter__author__claimed_by=user) |
                    Q(newsletter__author_profile__user=user)
                )
            else:
                qs = qs.filter(status=AuthorNewsletterIssue.IssueStatus.SENT)

        return qs.order_by('-sent_at', '-created_at')

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        instance = self.get_object()
        author = instance.newsletter.author
        is_owner = (
            (instance.newsletter.author_profile and instance.newsletter.author_profile.user_id == user.id) or
            (author and author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para modificar esta entrega.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        author = instance.newsletter.author
        is_owner = (
            (instance.newsletter.author_profile and instance.newsletter.author_profile.user_id == user.id) or
            (author and author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No tienes permisos para eliminar esta entrega.")
        instance.delete()

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def send_issue(self, request, pk=None):
        from django.utils import timezone
        issue = self.get_object()
        user = request.user
        author = issue.newsletter.author
        is_owner = (
            (issue.newsletter.author_profile and issue.newsletter.author_profile.user_id == user.id) or
            (author and author.claimed_by_id == user.id) or
            user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
        )
        if not is_owner:
            return Response({'detail': 'No tienes permisos para enviar esta entrega.'}, status=status.HTTP_403_FORBIDDEN)

        recipients_count = issue.newsletter.subscribers.filter(is_active=True).count()
        issue.status = AuthorNewsletterIssue.IssueStatus.SENT
        issue.sent_at = timezone.now()
        issue.recipients_count = recipients_count
        issue.save(update_fields=['status', 'sent_at', 'recipients_count', 'updated_at'])

        serializer = AuthorNewsletterIssueSerializer(issue, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)







from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    Author,
    AuthorAnnouncement,
    AuthorClaim,
    AuthorClaimStatus,
    AuthorEvent,
    AuthorEventAttendee,
    AuthorProfile,
    Book,
    Category,
    Errata,
    FAQ,
    LegalDocument,
    ReadingList,
    ReadingListCollaborator,
    ReadingListComment,
    ReadingListItem,
    RecommendationFeedback,
    Review,
    ReviewComment,
    UserBook,
    normalize_isbn,
    normalize_title,
)

User = get_user_model()


class AuthorBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'cover', 'published_date')

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from .media_utils import build_media_url
        if instance.cover:
            ret['cover'] = build_media_url(instance.cover, request=request)
        return ret


class AuthorBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'name', 'biography', 'photo')

    def validate_photo(self, value):
        """
        Valida y sanitiza la fotografía del autor.
        Asegura formato permitido, dimensiones, cuota <= 5MB y elimina metadatos EXIF.
        """
        if not value:
            return value
        from django.core.exceptions import ValidationError as DjangoValidationError

        from mybookconnect.media_security import (
            AUTHOR_PHOTO_PRESET,
            sanitize_image,
            validate_author_photo,
        )

        try:
            validate_author_photo(value)
            return sanitize_image(value, max_dimensions=AUTHOR_PHOTO_PRESET)
        except DjangoValidationError as err:
            msg = err.messages if hasattr(err, 'messages') else str(err)
            raise serializers.ValidationError(msg) from err

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from .media_utils import build_media_url
        if instance.photo:
            ret['photo'] = build_media_url(instance.photo, request=request)
        return ret


class AuthorSerializer(serializers.ModelSerializer):
    books = AuthorBookSerializer(many=True, read_only=True)
    published_books_count = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    total_reviews_count = serializers.SerializerMethodField()
    total_readers_count = serializers.SerializerMethodField()
    is_claimed = serializers.SerializerMethodField()
    can_claim = serializers.SerializerMethodField()

    class Meta:
        model = Author
        fields = (
            'id', 'name', 'biography', 'photo', 'nationality',
            'birth_date', 'death_date', 'website', 'twitter', 'instagram',
            'wikipedia_url', 'canonical_name', 'aliases', 'external_ids',
            'is_verified', 'claimed_by', 'books', 'published_books_count',
            'average_rating', 'total_reviews_count', 'total_readers_count',
            'is_claimed', 'can_claim'
        )
        read_only_fields = ('id', 'is_verified', 'claimed_by')

    @extend_schema_field(serializers.IntegerField)
    def get_published_books_count(self, obj):
        book_ids = set(obj.books.values_list('id', flat=True)).union(set(obj.all_books.values_list('id', flat=True)))
        return len(book_ids)

    @extend_schema_field(serializers.FloatField)
    def get_average_rating(self, obj):
        from django.db.models import Avg
        from .models import Book
        book_ids = set(obj.books.values_list('id', flat=True)).union(set(obj.all_books.values_list('id', flat=True)))
        if not book_ids:
            return 0.0
        avg = Book.objects.filter(id__in=book_ids, average_rating__isnull=False).aggregate(Avg('average_rating'))['average_rating__avg']
        return round(float(avg), 2) if avg is not None else 0.0

    @extend_schema_field(serializers.IntegerField)
    def get_total_reviews_count(self, obj):
        from .models import Review
        book_ids = set(obj.books.values_list('id', flat=True)).union(set(obj.all_books.values_list('id', flat=True)))
        if not book_ids:
            return 0
        return Review.objects.filter(book_id__in=book_ids, deleted_at__isnull=True).count()

    @extend_schema_field(serializers.IntegerField)
    def get_total_readers_count(self, obj):
        from .models import UserBook
        book_ids = set(obj.books.values_list('id', flat=True)).union(set(obj.all_books.values_list('id', flat=True)))
        if not book_ids:
            return 0
        return UserBook.objects.filter(book_id__in=book_ids).values('user_id').distinct().count()

    @extend_schema_field(serializers.BooleanField)
    def get_is_claimed(self, obj):
        return obj.claimed_by is not None or getattr(obj, 'is_verified', False)

    @extend_schema_field(serializers.BooleanField)
    def get_can_claim(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        if obj.claimed_by is not None or getattr(obj, 'is_verified', False):
            return False
        return True

    def validate_photo(self, value):
        """
        Valida y sanitiza la fotografía del autor.
        Asegura formato permitido, dimensiones, cuota <= 5MB y elimina metadatos EXIF.
        """
        if not value:
            return value
        from django.core.exceptions import ValidationError as DjangoValidationError

        from mybookconnect.media_security import (
            AUTHOR_PHOTO_PRESET,
            sanitize_image,
            validate_author_photo,
        )

        try:
            validate_author_photo(value)
            return sanitize_image(value, max_dimensions=AUTHOR_PHOTO_PRESET)
        except DjangoValidationError as err:
            msg = err.messages if hasattr(err, 'messages') else str(err)
            raise serializers.ValidationError(msg) from err

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from .media_utils import build_media_url
        if instance.photo:
            ret['photo'] = build_media_url(instance.photo, request=request)
        return ret


class CategorySerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class BookSerializer(serializers.ModelSerializer):
    author = AuthorBasicSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True
    )
    authors = AuthorBasicSerializer(many=True, read_only=True)
    author_ids = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), many=True, write_only=True, required=False
    )
    author_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )
    categories = CategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), many=True, source='categories', write_only=True, required=False
    )
    rating_distribution = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'author', 'author_id', 'authors', 'author_ids', 'author_names', 'isbn',
            'additional_isbns', 'google_volume_id', 'openlibrary_work_id', 'openlibrary_edition_id',
            'cover', 'description', 'published_date', 'average_rating', 'created_at',
            'categories', 'category_ids', 'rating_distribution', 'reviews_count'
        )
        read_only_fields = ('additional_isbns',)

    def create(self, validated_data):
        author_ids = validated_data.pop('author_ids', None)
        author_names = validated_data.pop('author_names', None)
        category_ids = validated_data.pop('categories', None)
        isbn = validated_data.get('isbn')
        title = validated_data.get('title')

        # 1. Resolver autor potencial
        resolved_author = validated_data.get('author')
        if not resolved_author and author_ids:
            resolved_author = author_ids[0]
        elif not resolved_author and author_names:
            first_name = str(author_names[0]).strip()
            if first_name:
                resolved_author, _ = Author.objects.get_or_create(name=first_name)

        # 2. Comprobar si ya existe por ISBN directo o alternativo
        existing = None
        if isbn:
            existing = Book.find_by_isbn(isbn)

        # 3. Comprobar si ya existe por Autor y Título Normalizado (ej. físico vs digital)
        if not existing and title:
            norm_title = normalize_title(title)
            candidates = Book.objects.filter(author=resolved_author) if resolved_author else Book.objects.filter(author__isnull=True)
            for c in candidates:
                if normalize_title(c.title) == norm_title:
                    existing = c
                    break

        # Si ya existe un libro equivalente, unificarlo en vez de crear un duplicado
        if existing:
            changed = False
            if isbn and existing.add_isbn(isbn):
                changed = True
            if category_ids:
                existing.categories.add(*category_ids)
            if author_ids:
                existing.authors.add(*author_ids)
            if not existing.description and validated_data.get('description'):
                existing.description = validated_data.get('description')
                changed = True
            if not existing.cover and validated_data.get('cover'):
                existing.cover = validated_data.get('cover')
                changed = True
            if not existing.author and resolved_author:
                existing.author = resolved_author
                changed = True
            if changed:
                existing.save()
            return existing

        book = super().create(validated_data)

        if category_ids is not None:
            book.categories.set(category_ids)

        if author_ids is not None:
            book.authors.set(author_ids)
            if not book.author and author_ids:
                book.author = author_ids[0]
                book.save(update_fields=['author'])
        elif book.author_id:
            book.authors.add(book.author)

        if author_names:
            for name in author_names:
                clean_name = str(name).strip()
                if clean_name:
                    author_obj, _ = Author.objects.get_or_create(name=clean_name)
                    book.authors.add(author_obj)
            if not book.author and book.authors.exists():
                book.author = book.authors.first()
                book.save(update_fields=['author'])

        return book

    def update(self, instance, validated_data):
        author_ids = validated_data.pop('author_ids', None)
        author_names = validated_data.pop('author_names', None)

        book = super().update(instance, validated_data)

        if author_ids is not None:
            book.authors.set(author_ids)
            if author_ids and not book.author:
                book.author = author_ids[0]
                book.save(update_fields=['author'])
        if author_names is not None:
            for name in author_names:
                clean_name = str(name).strip()
                if clean_name:
                    author_obj, _ = Author.objects.get_or_create(name=clean_name)
                    book.authors.add(author_obj)
            if not book.author and book.authors.exists():
                book.author = book.authors.first()
                book.save(update_fields=['author'])

        return book

    @extend_schema_field(serializers.DictField)
    def get_rating_distribution(self, obj):
        if hasattr(obj, '_precomputed_rating_distribution'):
            return obj._precomputed_rating_distribution

        request = self.context.get('request')
        cache_key = f'_rating_dist_{obj.id}'
        if request and hasattr(request, cache_key):
            return getattr(request, cache_key)

        from django.db.models import Count
        distribution = dict.fromkeys(range(1, 6), 0)
        reviews = Review.objects.filter(
            book=obj, rating__isnull=False, deleted_at__isnull=True, is_moderated=False
        ).values('rating').annotate(count=Count('id'))
        for r in reviews:
            val = r['rating']
            if 1 <= val <= 5:
                distribution[val] = r['count']
        if request:
            setattr(request, cache_key, distribution)
        return distribution

    @extend_schema_field(serializers.IntegerField)
    def get_reviews_count(self, obj):
        if hasattr(obj, 'annotated_reviews_count'):
            return obj.annotated_reviews_count
        request = self.context.get('request')
        cache_key = f'_reviews_count_{obj.id}'
        if request and hasattr(request, cache_key):
            return getattr(request, cache_key)

        count = Review.objects.filter(book=obj, deleted_at__isnull=True, is_moderated=False).count()
        if request:
            setattr(request, cache_key, count)
        return count

    def validate_cover(self, value):
        """
        Valida y sanitiza la portada del libro.
        Asegura formato permitido, dimensiones, cuota <= 10MB y elimina metadatos EXIF.
        """
        if not value:
            return value
        from django.core.exceptions import ValidationError as DjangoValidationError

        from mybookconnect.media_security import (
            COVER_PRESET,
            sanitize_image,
            validate_cover_image,
        )

        try:
            validate_cover_image(value)
            return sanitize_image(value, max_dimensions=COVER_PRESET)
        except DjangoValidationError as err:
            msg = err.messages if hasattr(err, 'messages') else str(err)
            raise serializers.ValidationError(msg) from err

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from .media_utils import build_media_url
        if instance.cover:
            ret['cover'] = build_media_url(instance.cover, request=request)
        return ret


class UserBookSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), source='book', write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = UserBook
        fields = (
            'id', 'book', 'book_id', 'status', 'status_display', 'progress',
            'current_page', 'started_at', 'finished_at',
            'is_read', 'rating', 'is_digital', 'owned', 'wishlist', 'notes', 'updated_at'
        )

    def validate_rating(self, value):
        if value is not None and not (1 <= value <= 5):
            raise serializers.ValidationError("La puntuación debe estar comprendida entre 1 y 5.")
        return value

    def validate_progress(self, value):
        if value is not None and not (0 <= value <= 100):
            raise serializers.ValidationError("El progreso debe estar comprendido entre 0 y 100%.")
        return value

    def validate_current_page(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("El número de página no puede ser negativo.")
        return value


class ReviewCommentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'avatar')


class ReviewCommentSerializer(serializers.ModelSerializer):
    user = ReviewCommentUserSerializer(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ReviewComment
        fields = ('id', 'review', 'user', 'content', 'created_at', 'updated_at', 'is_owner')
        read_only_fields = ('id', 'review', 'user', 'created_at', 'updated_at', 'is_owner')

    @extend_schema_field(serializers.BooleanField)
    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id or request.user.is_staff or request.user.is_superuser
        return False

    def validate_content(self, value):
        from mybookconnect.html_sanitizer import sanitize_plain_text
        return sanitize_plain_text(value)


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    privacy_level = serializers.CharField(source='user.privacy_level', read_only=True)
    is_friend = serializers.SerializerMethodField()
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), source='book', write_only=True)
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Calificación pública de 1 a 5 estrellas.",
    )
    likes_count = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Review
        fields = (
            'id', 'user', 'username', 'user_id', 'user_avatar', 'avatar', 'privacy_level', 'is_friend',
            'book', 'book_id', 'rating', 'title', 'text', 'image', 'created_at', 'updated_at',
            'likes_count', 'user_has_liked', 'comments_count'
        )

    @extend_schema_field(serializers.BooleanField())
    def get_is_friend(self, obj):
        if hasattr(obj, 'is_friend'):
            return obj.is_friend
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if not hasattr(request, '_cached_following_ids'):
                request._cached_following_ids = set(request.user.following.values_list('id', flat=True))
            return obj.user_id in request._cached_following_ids
        return False

    @extend_schema_field(serializers.IntegerField())
    def get_likes_count(self, obj):
        annotated = getattr(obj, 'annotated_likes_count', None)
        if annotated is not None:
            return annotated
        if hasattr(obj, 'likes_count'):
            return obj.likes_count
        return obj.likes.count()

    @extend_schema_field(serializers.BooleanField())
    def get_user_has_liked(self, obj):
        annotated = getattr(obj, 'annotated_user_has_liked', None)
        if annotated is not None:
            return bool(annotated)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    @extend_schema_field(serializers.IntegerField())
    def get_comments_count(self, obj):
        annotated = getattr(obj, 'annotated_comments_count', None)
        if annotated is not None:
            return annotated
        if hasattr(obj, 'comments_count'):
            return obj.comments_count
        return obj.comments.filter(deleted_at__isnull=True).count()

    def validate_title(self, value):
        from mybookconnect.html_sanitizer import sanitize_plain_text
        return sanitize_plain_text(value)

    def validate_text(self, value):
        from mybookconnect.html_sanitizer import sanitize_html
        return sanitize_html(value)

    def validate_image(self, value):
        if not value:
            return value
        from django.core.exceptions import ValidationError as DjangoValidationError

        from mybookconnect.media_security import COVER_PRESET, sanitize_image, validate_cover_image
        try:
            validate_cover_image(value)
            return sanitize_image(value, max_dimensions=COVER_PRESET)
        except DjangoValidationError as err:
            msg = err.messages if hasattr(err, 'messages') else str(err)
            raise serializers.ValidationError(msg) from err

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request') if hasattr(self, 'context') else None
        from .media_utils import build_media_url
        if instance.image:
            ret['image'] = build_media_url(instance.image, request=request)
        return ret



class ErrataSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    editor = serializers.StringRelatedField(read_only=True)
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source='book', write_only=True, required=False, allow_null=True
    )
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = Errata
        fields = (
            'id', 'user', 'book', 'book_id', 'author', 'author_id',
            'type', 'text', 'status', 'resolution_notes', 'editor', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'editor', 'created_at', 'updated_at')


class LegalDocumentSerializer(serializers.ModelSerializer):
    updated_by_username = serializers.ReadOnlyField(source='updated_by.username')

    class Meta:
        model = LegalDocument
        fields = ('id', 'slug', 'title', 'content', 'updated_at', 'updated_by', 'updated_by_username')
        read_only_fields = ('id', 'updated_at', 'updated_by', 'updated_by_username')


class AdminUserSerializer(serializers.ModelSerializer):
    books_count = serializers.IntegerField(source='user_books.count', read_only=True)
    reviews_count = serializers.IntegerField(source='reviews.count', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'is_staff', 'is_superuser', 'is_editor', 'role',
            'date_joined', 'last_login', 'privacy_level', 'books_count', 'reviews_count'
        )
        read_only_fields = ('id', 'username', 'date_joined', 'last_login', 'books_count', 'reviews_count')


class ReadingListUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'avatar')


class ReadingListItemSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(), source='book', write_only=True
    )
    added_by = ReadingListUserSerializer(read_only=True)

    class Meta:
        model = ReadingListItem
        fields = ('id', 'reading_list', 'book', 'book_id', 'position', 'notes', 'added_by', 'added_at')
        read_only_fields = ('id', 'reading_list', 'added_by', 'added_at')


class ReadingListCollaboratorSerializer(serializers.ModelSerializer):
    user = ReadingListUserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True, required=False
    )
    invited_by = ReadingListUserSerializer(read_only=True)

    class Meta:
        model = ReadingListCollaborator
        fields = (
            'id', 'reading_list', 'user', 'user_id', 'role',
            'status', 'can_add_books', 'can_remove_books',
            'invited_by', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'reading_list', 'invited_by', 'created_at', 'updated_at')


class ReadingListSerializer(serializers.ModelSerializer):
    user = ReadingListUserSerializer(read_only=True)
    items = ReadingListItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    collaborators_count = serializers.SerializerMethodField()
    collaborators = serializers.SerializerMethodField()
    is_collaborator = serializers.SerializerMethodField()

    class Meta:
        model = ReadingList
        fields = (
            'id', 'user', 'name', 'slug', 'description', 'privacy',
            'is_collaborative', 'created_at', 'updated_at', 'items', 'items_count',
            'followers_count', 'comments_count', 'views_count', 'is_following',
            'collaborators_count', 'collaborators', 'is_collaborator'
        )
        read_only_fields = ('id', 'user', 'slug', 'created_at', 'updated_at', 'views_count')

    @extend_schema_field(serializers.IntegerField())
    def get_items_count(self, obj):
        return obj.items.count()

    @extend_schema_field(serializers.IntegerField())
    def get_followers_count(self, obj):
        return obj.followers.count()

    @extend_schema_field(serializers.IntegerField())
    def get_comments_count(self, obj):
        return obj.comments.filter(deleted_at__isnull=True, is_moderated=False).count()

    @extend_schema_field(serializers.BooleanField())
    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(user=request.user).exists()
        return False

    @extend_schema_field(serializers.IntegerField())
    def get_collaborators_count(self, obj):
        if not obj.is_collaborative:
            return 0
        return obj.collaborators.filter(status=ReadingListCollaborator.Status.ACCEPTED).count()

    def get_collaborators(self, obj):
        if not obj.is_collaborative:
            return []
        collabs = obj.collaborators.filter(status=ReadingListCollaborator.Status.ACCEPTED).select_related('user')[:5]
        return ReadingListCollaboratorSerializer(collabs, many=True).data

    @extend_schema_field(serializers.BooleanField())
    def get_is_collaborator(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated or not obj.is_collaborative:
            return False
        return obj.collaborators.filter(user=request.user, status=ReadingListCollaborator.Status.ACCEPTED).exists()


class ReadingListCommentSerializer(serializers.ModelSerializer):
    """Serializador para comentarios en listas de lectura (Fase 21)."""
    user = ReadingListUserSerializer(read_only=True)
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = ReadingListComment
        fields = ('id', 'reading_list', 'user', 'content', 'created_at', 'updated_at', 'can_delete')
        read_only_fields = ('id', 'reading_list', 'user', 'created_at', 'updated_at')

    @extend_schema_field(serializers.BooleanField())
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.user_id == request.user.id or request.user.is_staff


class ReadingListCreateUpdateSerializer(serializers.ModelSerializer):
    user = ReadingListUserSerializer(read_only=True)

    class Meta:
        model = ReadingList
        fields = ('id', 'user', 'name', 'slug', 'description', 'privacy', 'is_collaborative')
        read_only_fields = ('id', 'user', 'slug')


class RecommendationFeedbackSerializer(serializers.ModelSerializer):
    """
    Serializador para registrar y representar eventos de feedback de recomendaciones.
    """
    user_username = serializers.CharField(source='user.username', read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(
        queryset=Book.objects.all(),
        source='book',
        write_only=True,
    )
    book_title = serializers.CharField(source='book.title', read_only=True)

    class Meta:
        model = RecommendationFeedback
        fields = (
            'id',
            'recommendation_id',
            'user',
            'user_username',
            'book_id',
            'book_title',
            'action',
            'strategy',
            'algorithm_version',
            'metadata',
            'created_at',
        )
        read_only_fields = ('id', 'user', 'user_username', 'book_title', 'created_at')


class SearchScoreBreakdownSerializer(serializers.Serializer):
    text_score = serializers.FloatField()
    fuzzy_score = serializers.FloatField()
    semantic_score = serializers.FloatField()


class UnifiedSearchResultSerializer(serializers.Serializer):
    book = BookSerializer()
    unified_score = serializers.FloatField()
    match_type = serializers.CharField()
    scores = SearchScoreBreakdownSerializer(source='*')


class UnifiedSearchResponseSerializer(serializers.Serializer):
    query = serializers.CharField()
    mode = serializers.CharField()
    count = serializers.IntegerField()
    total = serializers.IntegerField()
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    results = UnifiedSearchResultSerializer(many=True)


class AuthorProfileSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    author_name = serializers.CharField(source='author.name', read_only=True, allow_null=True)

    class Meta:
        model = AuthorProfile
        fields = (
            'id',
            'user',
            'user_username',
            'author',
            'author_name',
            'pen_name',
            'bio',
            'website',
            'twitter',
            'instagram',
            'is_verified',
            'verification_notes',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'user', 'user_username', 'is_verified', 'created_at', 'updated_at')


class AuthorAnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_photo = serializers.SerializerMethodField()
    book_title = serializers.CharField(source='book.title', read_only=True, allow_null=True)
    book_cover = serializers.SerializerMethodField()
    publication_type_display = serializers.CharField(source='get_publication_type_display', read_only=True)

    class Meta:
        model = AuthorAnnouncement
        fields = (
            'id',
            'author_profile',
            'author',
            'author_name',
            'author_photo',
            'book',
            'book_title',
            'book_cover',
            'title',
            'content',
            'excerpt',
            'publication_type',
            'publication_type_display',
            'has_spoilers',
            'spoiler_warning',
            'estimated_reading_time',
            'is_pinned',
            'is_draft',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'author_profile',
            'author_name',
            'author_photo',
            'book_title',
            'book_cover',
            'publication_type_display',
            'created_at',
            'updated_at',
        )

    def get_author_name(self, obj) -> str:
        if obj.author:
            return obj.author.name
        if obj.author_profile.pen_name:
            return obj.author_profile.pen_name
        if obj.author_profile.author:
            return obj.author_profile.author.name
        return obj.author_profile.user.username

    def get_author_photo(self, obj):
        request = self.context.get('request')
        photo = None
        if obj.author and obj.author.photo:
            photo = obj.author.photo
        elif obj.author_profile and obj.author_profile.author and obj.author_profile.author.photo:
            photo = obj.author_profile.author.photo
        if photo:
            from .media_utils import build_media_url
            return build_media_url(photo, request=request)
        return None

    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book and obj.book.cover:
            from .media_utils import build_media_url
            return build_media_url(obj.book.cover, request=request)
        return None


class AuthorAnnouncementCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorAnnouncement
        fields = (
            'id',
            'author',
            'book',
            'title',
            'content',
            'excerpt',
            'publication_type',
            'has_spoilers',
            'spoiler_warning',
            'estimated_reading_time',
            'is_pinned',
            'is_draft',
        )

    def validate(self, attrs):
        title = attrs.get('title')
        content = attrs.get('content')
        if title is not None and not title.strip():
            raise serializers.ValidationError({'title': 'El título no puede estar vacío.'})
        if content is not None and not content.strip():
            raise serializers.ValidationError({'content': 'El contenido no puede estar vacío.'})
        return attrs


class AuthorClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorClaim
        fields = ('id', 'proof_description', 'contact_email', 'supporting_link')

    def validate(self, attrs):
        author = self.context.get('author')
        user = self.context.get('user')
        if not author:
            raise serializers.ValidationError('Autor no especificado.')
        if author.claimed_by is not None and author.claimed_by != user:
            raise serializers.ValidationError('Esta página de autor ya ha sido reclamada y verificada.')
        existing_pending = AuthorClaim.objects.filter(
            author=author,
            user=user,
            status=AuthorClaimStatus.PENDING,
        ).exists()
        if existing_pending:
            raise serializers.ValidationError('Ya tienes una solicitud de reclamación pendiente para este autor.')
        return attrs

    def create(self, validated_data):
        author = self.context['author']
        user = self.context['user']
        return AuthorClaim.objects.create(
            author=author,
            user=user,
            **validated_data
        )


class AuthorClaimAdminSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    author_photo = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = AuthorClaim
        fields = (
            'id', 'author_id', 'author_name', 'author_photo',
            'user', 'username', 'user_email', 'status',
            'proof_description', 'contact_email', 'supporting_link',
            'moderation_notes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_author_photo(self, obj):
        request = self.context.get('request')
        if obj.author and obj.author.photo:
            from .media_utils import build_media_url
            return build_media_url(obj.author.photo, request=request)
        return None


class FAQSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = FAQ
        fields = (
            'id', 'question', 'answer', 'category', 'category_display',
            'order', 'is_published', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class AuthorEventAttendeeSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AuthorEventAttendee
        fields = (
            'id', 'event', 'user', 'username', 'user_avatar',
            'status', 'status_display', 'notes', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'status_display')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_avatar(self, obj):
        request = self.context.get('request')
        avatar = getattr(obj.user, 'avatar', None)
        if avatar:
            from .media_utils import build_media_url
            return build_media_url(avatar, request=request)
        return None


class AuthorEventSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.name', read_only=True)
    author_photo = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    book_title = serializers.CharField(source='book.title', read_only=True, allow_null=True)
    book_cover = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    event_format_display = serializers.CharField(source='get_event_format_display', read_only=True)
    registered_count = serializers.IntegerField(read_only=True)
    waitlist_count = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    user_registration_status = serializers.SerializerMethodField()
    is_user_registered = serializers.SerializerMethodField()
    user_notes = serializers.SerializerMethodField()

    class Meta:
        model = AuthorEvent
        fields = (
            'id', 'author', 'author_name', 'author_photo', 'author_profile',
            'created_by', 'created_by_username', 'book', 'book_title', 'book_cover',
            'title', 'description', 'event_type', 'event_type_display',
            'event_format', 'event_format_display', 'start_time', 'end_time',
            'event_timezone', 'location_name', 'location_address', 'online_url',
            'max_attendees', 'is_cancelled', 'registered_count', 'waitlist_count',
            'is_full', 'user_registration_status', 'is_user_registered', 'user_notes',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_author_photo(self, obj):
        request = self.context.get('request')
        if obj.author and obj.author.photo:
            from .media_utils import build_media_url
            return build_media_url(obj.author.photo, request=request)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_book_cover(self, obj):
        request = self.context.get('request')
        if obj.book and obj.book.cover:
            from .media_utils import build_media_url
            return build_media_url(obj.book.cover, request=request)
        return None

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_registration_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        attendee = obj.attendees.filter(user=request.user).first()
        return attendee.status if attendee else None

    @extend_schema_field(serializers.BooleanField)
    def get_is_user_registered(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.attendees.filter(user=request.user, status=AuthorEventAttendee.AttendeeStatus.REGISTERED).exists()

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_user_notes(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        attendee = obj.attendees.filter(user=request.user).first()
        return attendee.notes if attendee else None


class AuthorEventCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorEvent
        fields = (
            'author', 'book', 'title', 'description',
            'event_type', 'event_format', 'start_time', 'end_time',
            'event_timezone', 'location_name', 'location_address',
            'online_url', 'max_attendees', 'is_cancelled'
        )

    def validate(self, attrs):
        start_time = attrs.get('start_time') or (self.instance.start_time if self.instance else None)
        end_time = attrs.get('end_time') if 'end_time' in attrs else (self.instance.end_time if self.instance else None)

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "La fecha y hora de finalización debe ser posterior al inicio."})

        request = self.context.get('request')
        author = attrs.get('author') or (self.instance.author if self.instance else None)
        if request and author:
            user = request.user
            is_claimed_owner = (author.claimed_by_id == user.id)
            is_profile_owner = hasattr(user, 'author_profile') and user.author_profile.author_id == author.id and user.author_profile.is_verified
            is_staff = user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'MODERATOR')
            if not (is_claimed_owner or is_profile_owner or is_staff):
                raise serializers.ValidationError({"author": "No tienes permisos para organizar eventos para este autor."})

        return attrs




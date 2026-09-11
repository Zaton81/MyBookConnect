from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Author,
    Book,
    Category,
    Errata,
    LegalDocument,
    ReadingList,
    ReadingListItem,
    Review,
    ReviewComment,
    UserBook,
)

User = get_user_model()


class AuthorBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'cover', 'published_date')


class AuthorBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'name', 'biography', 'photo')


class AuthorSerializer(serializers.ModelSerializer):
    books = AuthorBookSerializer(many=True, read_only=True)

    class Meta:
        model = Author
        fields = ('id', 'name', 'biography', 'photo', 'books')


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')


class BookSerializer(serializers.ModelSerializer):
    author = AuthorBasicSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True
    )
    categories = CategorySerializer(many=True, read_only=True)
    rating_distribution = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'author', 'author_id', 'isbn',
            'google_volume_id', 'openlibrary_work_id', 'openlibrary_edition_id',
            'cover', 'description', 'published_date', 'average_rating', 'created_at',
            'categories', 'rating_distribution', 'reviews_count'
        )

    def get_rating_distribution(self, obj):
        from django.db.models import Count
        distribution = dict.fromkeys(range(1, 11), 0)
        reviews = Review.objects.filter(book=obj, rating__isnull=False).values('rating').annotate(count=Count('id'))
        for r in reviews:
            val = r['rating']
            if 1 <= val <= 10:
                distribution[val] = r['count']
        return distribution

    def get_reviews_count(self, obj):
        if hasattr(obj, 'annotated_reviews_count'):
            return obj.annotated_reviews_count
        return Review.objects.filter(book=obj).count()


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

    def get_is_owner(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.user_id == request.user.id or request.user.is_staff or request.user.is_superuser
        return False


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
    likes_count = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            'id', 'user', 'username', 'user_id', 'user_avatar', 'avatar', 'privacy_level', 'is_friend',
            'book', 'book_id', 'rating', 'title', 'text', 'created_at', 'updated_at',
            'likes_count', 'user_has_liked', 'comments_count'
        )

    def get_is_friend(self, obj):
        if hasattr(obj, 'is_friend'):
            return obj.is_friend
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.following.filter(id=obj.user.id).exists()
        return False

    def get_likes_count(self, obj):
        annotated = getattr(obj, 'annotated_likes_count', None)
        if annotated is not None:
            return annotated
        if hasattr(obj, 'likes_count'):
            return obj.likes_count
        return obj.likes.count()

    def get_user_has_liked(self, obj):
        annotated = getattr(obj, 'annotated_user_has_liked', None)
        if annotated is not None:
            return bool(annotated)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_comments_count(self, obj):
        annotated = getattr(obj, 'annotated_comments_count', None)
        if annotated is not None:
            return annotated
        if hasattr(obj, 'comments_count'):
            return obj.comments_count
        return obj.comments.filter(deleted_at__isnull=True).count()




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
            'is_active', 'is_staff', 'is_superuser', 'is_editor',
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

    class Meta:
        model = ReadingListItem
        fields = ('id', 'reading_list', 'book', 'book_id', 'position', 'notes', 'added_at')
        read_only_fields = ('id', 'reading_list', 'added_at')


class ReadingListSerializer(serializers.ModelSerializer):
    user = ReadingListUserSerializer(read_only=True)
    items = ReadingListItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = ReadingList
        fields = (
            'id', 'user', 'name', 'slug', 'description', 'privacy',
            'created_at', 'updated_at', 'items', 'items_count',
            'followers_count', 'is_following'
        )
        read_only_fields = ('id', 'user', 'slug', 'created_at', 'updated_at')

    def get_items_count(self, obj):
        return obj.items.count()

    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.followers.filter(user=request.user).exists()
        return False


class ReadingListCreateUpdateSerializer(serializers.ModelSerializer):
    user = ReadingListUserSerializer(read_only=True)

    class Meta:
        model = ReadingList
        fields = ('id', 'user', 'name', 'slug', 'description', 'privacy')
        read_only_fields = ('id', 'user', 'slug')


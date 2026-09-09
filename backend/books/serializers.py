from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Author, Book, Category, Errata, LegalDocument, Review, UserBook

User = get_user_model()


class AuthorBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ('id', 'title', 'cover', 'published_date')


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
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True
    )
    categories = CategorySerializer(many=True, read_only=True)
    rating_distribution = serializers.SerializerMethodField()
    reviews_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'author', 'author_id', 'isbn', 'cover',
            'description', 'published_date', 'average_rating', 'created_at',
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
        return Review.objects.filter(book=obj).count()


class UserBookSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), source='book', write_only=True)

    class Meta:
        model = UserBook
        fields = ('id', 'book', 'book_id', 'is_read', 'rating', 'is_digital', 'owned', 'wishlist', 'notes', 'updated_at')


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    privacy_level = serializers.CharField(source='user.privacy_level', read_only=True)
    is_friend = serializers.SerializerMethodField()
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), source='book', write_only=True)

    class Meta:
        model = Review
        fields = (
            'id', 'user', 'user_id', 'user_avatar', 'privacy_level', 'is_friend',
            'book', 'book_id', 'rating', 'title', 'text', 'created_at', 'updated_at'
        )

    def get_is_friend(self, obj):
        if hasattr(obj, 'is_friend'):
            return obj.is_friend
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.following.filter(id=obj.user.id).exists()
        return False


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

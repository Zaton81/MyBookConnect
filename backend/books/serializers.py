from rest_framework import serializers
from .models import Author, Book, Review, UserBook, Category


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
    author_id = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True)
    categories = CategorySerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'author', 'author_id', 'isbn', 'cover',
            'description', 'published_date', 'average_rating', 'created_at', 'categories'
        )


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
        fields = ('id', 'user', 'user_id', 'user_avatar', 'privacy_level', 'is_friend', 'book', 'book_id', 'rating', 'text', 'created_at')

    def get_is_friend(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Check if request.user follows the review author
            return request.user.following.filter(id=obj.user.id).exists()
        return False

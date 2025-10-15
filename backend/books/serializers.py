from rest_framework import serializers
from .models import Author, Book, Review, UserBook


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ('id', 'name', 'biography', 'photo')


class BookSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True)

    class Meta:
        model = Book
        fields = (
            'id', 'title', 'author', 'author_id', 'isbn', 'cover',
            'description', 'published_date', 'average_rating', 'created_at'
        )


class UserBookSerializer(serializers.ModelSerializer):
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), source='book', write_only=True)

    class Meta:
        model = UserBook
        fields = ('id', 'book', 'book_id', 'is_read', 'rating', 'is_digital', 'owned', 'wishlist', 'notes', 'updated_at')


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    book = BookSerializer(read_only=True)
    book_id = serializers.PrimaryKeyRelatedField(queryset=Book.objects.all(), source='book', write_only=True)

    class Meta:
        model = Review
        fields = ('id', 'user', 'book', 'book_id', 'rating', 'text', 'created_at')

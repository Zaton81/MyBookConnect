"""
Factory Boy / model factories for unified backend test fixtures.
"""
from django.contrib.auth import get_user_model
from reviews.models import Review

from books.models import Author, Book

User = get_user_model()


class UserFactory:
    @staticmethod
    def create(username="testuser", email="test@example.com", password="SecurePassword123!", **kwargs):
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            **kwargs,
        )
        return user


class AuthorFactory:
    @staticmethod
    def create(name="Autor de Prueba", **kwargs):
        return Author.objects.create(name=name, **kwargs)


class BookFactory:
    @staticmethod
    def create(title="Libro de Prueba", author=None, isbn="9780123456789", **kwargs):
        if not author:
            author = AuthorFactory.create()
        return Book.objects.create(title=title, author=author, isbn=isbn, **kwargs)


class ReviewFactory:
    @staticmethod
    def create(user=None, book=None, rating=5, text="Excelente lectura recomendada.", **kwargs):
        if not user:
            user = UserFactory.create(username="reviewer_auto")
        if not book:
            book = BookFactory.create()
        return Review.objects.create(user=user, book=book, rating=rating, text=text, **kwargs)

from django.contrib.auth import get_user_model
from django.db import connection
import pytest
from rest_framework.test import APIClient

from books.models import Author, Book, Category, Review, UserBook
from messages_app.models import Conversation, Message

User = get_user_model()


@pytest.mark.django_db
class TestDatabasePerformanceAndIndexes:
    def test_composite_indexes_exist_in_database(self):
        """Verifica que los índices compuestos definidos en PostgreSQL existan efectivamente en el catálogo."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname FROM pg_indexes
                WHERE schemaname = 'public';
                """
            )
            existing_indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = [
            'idx_book_title',
            'idx_book_title_author',
            'idx_book_created_at',
            'idx_review_book_created',
            'idx_review_user_created',
            'idx_review_created_at',
            'idx_userbook_read_updated',
            'idx_userbook_status_updated',
            'idx_errata_status_created',
            'idx_errata_book_status',
            'idx_msg_conv_created',
            'idx_msg_conv_read',
        ]

        for idx_name in expected_indexes:
            assert idx_name in existing_indexes, f"El índice {idx_name} no se encontró en PostgreSQL"

    def test_user_books_list_num_queries(self, django_assert_num_queries):
        """Verifica que listar UserBooks mantenga un número acotado de consultas mediante select_related y prefetch."""
        user = User.objects.create_user(username='lector_perf', email='perf@test.com', password='pwd')
        cat = Category.objects.create(name='Ficción')
        author = Author.objects.create(name='Autor Prueba')

        # Crear 6 libros con categorías asociadas
        for i in range(6):
            b = Book.objects.create(title=f'Libro {i}', author=author)
            b.categories.add(cat)
            UserBook.objects.create(user=user, book=b, is_read=True)

        client = APIClient()
        client.force_authenticate(user=user)

        # Con select_related('book', 'book__author') y prefetch_related('book__categories')
        with django_assert_num_queries(15):
            res = client.get('/api/v1/books/user/books/')
            assert res.status_code == 200
            assert len(res.json()['results']) == 6

    def test_reviews_list_num_queries(self, django_assert_num_queries):
        """Verifica que listar reseñas no dispare consultas N+1 sobre autores o categorías."""
        author = Author.objects.create(name='Autor Reseñas')
        book = Book.objects.create(title='Libro Reseñado', author=author)
        cat = Category.objects.create(name='Novela')
        book.categories.add(cat)

        for i in range(5):
            u = User.objects.create_user(username=f'revisor_{i}', email=f'rev{i}@test.com', password='pwd')
            Review.objects.create(user=u, book=book, rating=5, text=f'Reseña {i}')

        client = APIClient()
        # Con select_related('user', 'book', 'book__author'), prefetch_related('book__categories') y AuthorBasicSerializer
        with django_assert_num_queries(12):
            res = client.get(f'/api/v1/books/reviews/?book={book.id}')
            assert res.status_code == 200
            assert len(res.json()) == 5

    def test_messages_list_select_related_sender(self, django_assert_num_queries):
        """Verifica que consultar mensajes de un chat use select_related('sender') sin N+1."""
        u1 = User.objects.create_user(username='chat_u1', email='cu1@test.com', password='pwd')
        u2 = User.objects.create_user(username='chat_u2', email='cu2@test.com', password='pwd')
        conv = Conversation.objects.create()
        conv.participants.add(u1, u2)

        for i in range(5):
            sender = u1 if i % 2 == 0 else u2
            Message.objects.create(conversation=conv, sender=sender, text=f'Hola {i}')

        client = APIClient()
        client.force_authenticate(user=u1)

        # Consulta acotada gracias a select_related('sender')
        with django_assert_num_queries(2):
            res = client.get(f'/api/v1/chat/messages/?conversation={conv.id}')
            assert res.status_code == 200
            assert len(res.json()) == 5

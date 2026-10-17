from unittest.mock import patch

from django.contrib.auth import get_user_model
import pytest
from rest_framework.test import APIClient

from books.models import Author, Book, UserBook
from books.tasks import (
    download_cover_task,
    enrich_book_task,
    import_books_by_author_task,
    recalculate_book_rating_task,
    refresh_author_task,
)

User = get_user_model()


@pytest.mark.django_db
class TestCeleryTasks:
    def test_enrich_book_task_success(self):
        author = Author.objects.create(name='Gabriel García Márquez')
        book = Book.objects.create(title='Cien años de soledad', author=author)

        with patch('books.tasks.maybe_enrich_book') as mock_enrich:
            res = enrich_book_task.delay(book.id)
            assert res.get() is True
            mock_enrich.assert_called_once()

    def test_enrich_book_task_nonexistent_returns_false(self):
        res = enrich_book_task.delay(999999)
        assert res.get() is False

    def test_download_cover_task(self):
        author = Author.objects.create(name='Julio Cortázar')
        book = Book.objects.create(title='Rayuela', author=author)

        with patch('books.tasks.ensure_book_cover') as mock_cover:
            res = download_cover_task.delay(book.id)
            assert res.get() is False
            mock_cover.assert_called_once()

    def test_refresh_author_task(self):
        author = Author.objects.create(name='Jorge Luis Borges')

        with patch('books.tasks.maybe_enrich_author') as mock_author:
            res = refresh_author_task.delay(author.id)
            assert res.get() is True
            mock_author.assert_called_once()

    def test_recalculate_book_rating_task(self):
        author = Author.objects.create(name='Mario Vargas Llosa')
        book = Book.objects.create(title='La ciudad y los perros', author=author)
        u1 = User.objects.create_user(username='u1', email='u1@test.com', password='pwd')
        u2 = User.objects.create_user(username='u2', email='u2@test.com', password='pwd')

        UserBook.objects.create(user=u1, book=book, rating=4)
        UserBook.objects.create(user=u2, book=book, rating=5)

        res = recalculate_book_rating_task.delay(book.id)
        assert res.get() == 4.5

        book.refresh_from_db()
        assert book.average_rating == 4.5

    def test_import_books_by_author_task(self):
        with patch('books.tasks.import_books_by_author', return_value=3) as mock_import:
            res = import_books_by_author_task.delay('Miguel de Cervantes')
            assert res.get() == 3
            mock_import.assert_called_once_with('Miguel de Cervantes')

    def test_admin_enrich_endpoint_returns_202_and_task_id(self):
        admin = User.objects.create_user(
            username='staff_admin',
            email='staff@test.com',
            password='Password123!',
            is_staff=True,
        )
        author = Author.objects.create(name='Federico García Lorca')
        book = Book.objects.create(title='Bodas de sangre', author=author)

        client = APIClient()
        client.force_authenticate(user=admin)

        with patch('books.admin_views.enrich_book_task.delay') as mock_delay:
            class FakeTaskResult:
                id = 'fake-celery-task-id-123'

            mock_delay.return_value = FakeTaskResult()

            response = client.post(f'/api/v1/admin/books/{book.id}/enrich/')
            assert response.status_code == 202
            data = response.json()
            assert data['task_id'] == 'fake-celery-task-id-123'
            assert data['status'] == 'queued'
            mock_delay.assert_called_once_with(book.id)

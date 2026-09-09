import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from books.models import Author, Book, Errata, ErrataStatus, ErrataType, UserBook

User = get_user_model()


@pytest.fixture
def test_user():
    return User.objects.create_user(username='reader1', email='reader1@example.com', password='pass1234')


@pytest.fixture
def second_user():
    return User.objects.create_user(username='reader2', email='reader2@example.com', password='pass1234')


@pytest.fixture
def sample_book():
    author = Author.objects.create(name='Gabriel García Márquez', biography='Premio Nobel de Literatura.')
    book = Book.objects.create(
        title='Cien años de soledad',
        author=author,
        isbn='9788437604947',
        description='Historia de la familia Buendía en Macondo.'
    )
    return book


@pytest.mark.django_db
class TestDomainModels:
    def test_create_author_and_book(self, sample_book):
        assert sample_book.title == 'Cien años de soledad'
        assert sample_book.author.name == 'Gabriel García Márquez'
        assert sample_book.average_rating is None

    def test_userbook_creation_and_rating_calculation(self, test_user, second_user, sample_book):
        # User 1 rates 8
        UserBook.objects.create(
            user=test_user,
            book=sample_book,
            is_read=True,
            rating=8
        )
        sample_book.refresh_from_db()
        assert sample_book.average_rating == 8.0

        # User 2 rates 10
        UserBook.objects.create(
            user=second_user,
            book=sample_book,
            is_read=True,
            rating=10
        )
        sample_book.refresh_from_db()
        assert sample_book.average_rating == 9.0

        # UserBook unique together (user, book)
        with pytest.raises(IntegrityError):
            UserBook.objects.create(user=test_user, book=sample_book)

    def test_errata_creation(self, test_user, sample_book):
        errata = Errata.objects.create(
            user=test_user,
            book=sample_book,
            type=ErrataType.ERRATA,
            text='Falta el año de la primera edición (1967).'
        )
        assert errata.status == ErrataStatus.OPEN
        assert str(errata) == f"errata - {sample_book.title} (open)"

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

    def test_review_uniqueness_and_isolation(self, test_user, sample_book):
        from books.models import Review
        # Create public review
        review1 = Review.objects.create(
            user=test_user,
            book=sample_book,
            rating=9,
            title='Obra maestra',
            text='Un hito de la literatura universal.'
        )
        assert review1.rating == 9

        # UniqueConstraint prevents second review for same user and book
        from django.db import transaction
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(
                    user=test_user,
                    book=sample_book,
                    rating=5,
                    text='Intento duplicado'
                )

        # Creating or modifying personal UserBook does NOT overwrite public review
        ub = UserBook.objects.create(
            user=test_user,
            book=sample_book,
            is_read=False,
            notes='Mis notas privadas de lectura que nadie más debe ver'
        )

        review1.refresh_from_db()
        assert review1.text == 'Un hito de la literatura universal.'
        assert review1.text != ub.notes

        # Deleting personal UserBook does NOT delete the public review
        ub.delete()
        assert Review.objects.filter(id=review1.id).exists()

    def test_book_serializer_rating_distribution(self, test_user, second_user, sample_book):
        from books.models import Review
        from books.serializers import BookSerializer

        Review.objects.create(user=test_user, book=sample_book, rating=10, text='Excelente')
        Review.objects.create(user=second_user, book=sample_book, rating=8, text='Muy bueno')

        serializer = BookSerializer(sample_book)
        dist = serializer.data['rating_distribution']
        assert dist[10] == 1
        assert dist[8] == 1
        assert dist[1] == 0
        assert serializer.data['reviews_count'] == 2

    def test_reading_status_and_progress_tracking(self, test_user, sample_book):
        from books.models import ReadingStatus

        # 1. Start reading
        ub = UserBook.objects.create(
            user=test_user,
            book=sample_book,
            status=ReadingStatus.READING,
            current_page=150,
            progress=40,
        )
        assert ub.status == ReadingStatus.READING
        assert ub.is_read is False
        assert ub.progress == 40
        assert ub.current_page == 150
        assert ub.started_at is not None
        assert ub.finished_at is None

        # 2. Complete reading
        ub.status = ReadingStatus.READ
        ub.save()
        ub.refresh_from_db()
        assert ub.is_read is True
        assert ub.progress == 100
        assert ub.finished_at is not None

        # 3. Serialization check
        from books.serializers import UserBookSerializer
        data = UserBookSerializer(ub).data
        assert data['status'] == 'read'
        assert data['status_display'] == 'Leído'
        assert data['progress'] == 100

    def test_isbn_normalization_and_external_ids(self, sample_book):
        from books.models import normalize_isbn
        from books.serializers import BookSerializer

        assert normalize_isbn('978-84-376-0494-7') == '9788437604947'
        assert normalize_isbn('  0-13-235088-2  ') == '0132350882'
        assert normalize_isbn(None) is None

        sample_book.isbn = '978-84-123-4567-8'
        sample_book.google_volume_id = 'gvol12345'
        sample_book.openlibrary_work_id = 'OL99999W'
        sample_book.openlibrary_edition_id = 'OL88888M'
        sample_book.save()
        sample_book.refresh_from_db()

        assert sample_book.isbn == '9788412345678'
        assert sample_book.google_volume_id == 'gvol12345'
        assert sample_book.openlibrary_work_id == 'OL99999W'

        data = BookSerializer(sample_book).data
        assert data['google_volume_id'] == 'gvol12345'
        assert data['openlibrary_work_id'] == 'OL99999W'
        assert data['openlibrary_edition_id'] == 'OL88888M'

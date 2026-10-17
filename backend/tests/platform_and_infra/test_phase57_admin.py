import pytest
from django.contrib.admin.sites import site
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.admin import (
    AuthorAdmin,
    BookAdmin,
    ErrataAdmin,
    ProviderListFilter,
    RatingRangeFilter,
    ReviewAdmin,
)
from books.models import (
    Author,
    Book,
    Category,
    Errata,
    ErrataStatus,
    ErrataType,
    Review,
)
from users.admin import CustomUserAdmin, NotificationAdmin, ReportAdmin
from users.models import Notification, NotificationType, Report, UserRole

User = get_user_model()


class MockRequest:
    def __init__(self, user):
        self.user = user
        self.messages = []

    def message_user(self, request, msg):
        self.messages.append(msg)


@pytest.mark.django_db
class TestPhase57Administration:
    def setup_method(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True,
            role=UserRole.ADMIN,
        )
        self.regular_user = User.objects.create_user(
            username='regular_user',
            email='regular@example.com',
            password='Password123!',
        )
        self.author = Author.objects.create(
            name='Gabriel García Márquez',
            biography='Nobel Prize winning author from Colombia.',
        )
        self.category_fic = Category.objects.create(name='Ficción', slug='ficcion')
        self.category_cla = Category.objects.create(name='Clásicos', slug='clasicos')

        self.book1 = Book.objects.create(
            title='Cien años de soledad',
            author=self.author,
            isbn='9780307474728',
            google_volume_id='gvol123',
            average_rating=4.8,
            published_date='1967-05-30',
        )
        self.book1.categories.add(self.category_fic, self.category_cla)

        self.book2 = Book.objects.create(
            title='Crónica de una muerte anunciada',
            author=self.author,
            isbn='9788497592437',
            openlibrary_work_id='OL123W',
            average_rating=3.5,
            published_date='1981-01-01',
        )

    def test_django_admin_registrations_and_filters(self):
        # 1. Verificar registros en Django Admin
        assert Book in site._registry
        assert Author in site._registry
        assert Review in site._registry
        assert Errata in site._registry
        assert User in site._registry
        assert Report in site._registry
        assert Notification in site._registry

        book_admin = site._registry[Book]
        author_admin = site._registry[Author]
        review_admin = site._registry[Review]
        errata_admin = site._registry[Errata]
        user_admin = site._registry[User]
        report_admin = site._registry[Report]
        notif_admin = site._registry[Notification]

        assert isinstance(book_admin, BookAdmin)
        assert isinstance(author_admin, AuthorAdmin)
        assert isinstance(review_admin, ReviewAdmin)
        assert isinstance(errata_admin, ErrataAdmin)
        assert isinstance(user_admin, CustomUserAdmin)
        assert isinstance(report_admin, ReportAdmin)
        assert isinstance(notif_admin, NotificationAdmin)

        # 2. Probar ProviderListFilter
        req = MockRequest(self.admin_user)
        provider_filter = ProviderListFilter(None, {'provider': ['google']}, Book, book_admin)
        qs_google = provider_filter.queryset(req, Book.objects.all())
        assert self.book1 in qs_google
        assert self.book2 not in qs_google

        # 3. Probar RatingRangeFilter
        rating_filter = RatingRangeFilter(None, {'rating_range': ['high']}, Book, book_admin)
        qs_high = rating_filter.queryset(req, Book.objects.all())
        assert self.book1 in qs_high
        assert self.book2 not in qs_high

    def test_django_admin_actions(self):
        from unittest.mock import patch
        req = MockRequest(self.admin_user)

        # 1. BookAdmin actions
        book_admin = site._registry[Book]
        book_admin.message_user = lambda r, m: req.messages.append(m)
        with patch('books.admin.enrich_book_task.delay') as mock_enrich:
            book_admin.re_enrich_books(req, Book.objects.filter(id=self.book1.id))
            mock_enrich.assert_called_once_with(self.book1.id)
            self.book1.refresh_from_db()
            assert self.book1.enrichment_attempted is False
            assert any('re-enriquecimiento' in m for m in req.messages)

        book_admin.rebuild_embeddings(req, Book.objects.filter(id=self.book1.id))
        assert any('embedding' in m for m in req.messages)

        # 2. AuthorAdmin actions
        author_admin = site._registry[Author]
        author_admin.message_user = lambda r, m: req.messages.append(m)
        with patch('books.admin.refresh_author_task.delay') as mock_refresh:
            author_admin.re_enrich_authors(req, Author.objects.filter(id=self.author.id))
            mock_refresh.assert_called_once_with(self.author.id)
            self.author.refresh_from_db()
            assert self.author.enrichment_attempted is False

        # 3. ReviewAdmin actions
        rev = Review.objects.create(
            user=self.regular_user,
            book=self.book1,
            rating=5,
            text='Obra maestra imprescindible.',
        )
        review_admin = site._registry[Review]
        review_admin.message_user = lambda r, m: req.messages.append(m)

        review_admin.mark_as_moderated(req, Review.objects.filter(id=rev.id))
        rev.refresh_from_db()
        assert rev.is_moderated is True

        review_admin.unmark_as_moderated(req, Review.objects.filter(id=rev.id))
        rev.refresh_from_db()
        assert rev.is_moderated is False

        review_admin.soft_delete_reviews(req, Review.objects.filter(id=rev.id))
        rev.refresh_from_db()
        assert rev.deleted_at is not None

        review_admin.restore_reviews(req, Review.objects.filter(id=rev.id))
        rev.refresh_from_db()
        assert rev.deleted_at is None

        # 4. UserAdmin actions
        user_admin = site._registry[User]
        user_admin.message_user = lambda r, m: req.messages.append(m)

        user_admin.ban_users(req, User.objects.filter(id=self.regular_user.id))
        self.regular_user.refresh_from_db()
        assert self.regular_user.is_active is False

        user_admin.unban_users(req, User.objects.filter(id=self.regular_user.id))
        self.regular_user.refresh_from_db()
        assert self.regular_user.is_active is True

        user_admin.make_editor(req, User.objects.filter(id=self.regular_user.id))
        self.regular_user.refresh_from_db()
        assert self.regular_user.is_editor is True

        # 5. ErrataAdmin actions
        errata = Errata.objects.create(
            user=self.regular_user,
            book=self.book1,
            type=ErrataType.ERRATA,
            text='Error en año de publicación',
        )
        errata_admin = site._registry[Errata]
        errata_admin.message_user = lambda r, m: req.messages.append(m)
        errata_admin.approve_erratas(req, Errata.objects.filter(id=errata.id))
        errata.refresh_from_db()
        assert errata.status == ErrataStatus.APPROVED

        # 6. NotificationAdmin actions
        notif = Notification.objects.create(
            recipient=self.regular_user,
            type=NotificationType.SYSTEM,
            title='Test notif',
        )
        notif_admin = site._registry[Notification]
        notif_admin.message_user = lambda r, m: req.messages.append(m)
        notif_admin.mark_as_read(req, Notification.objects.filter(id=notif.id))
        notif.refresh_from_db()
        assert notif.read is True

    def test_api_admin_book_filtering_and_editing(self):
        self.client.force_authenticate(user=self.admin_user)

        # 1. Filtros de libros
        res_google = self.client.get('/api/v1/admin/books/?provider=google')
        assert res_google.status_code == status.HTTP_200_OK
        data_google = res_google.json()
        items = data_google if isinstance(data_google, list) else data_google.get('results', [])
        assert any(b['id'] == self.book1.id for b in items)
        assert not any(b['id'] == self.book2.id for b in items)

        res_rating = self.client.get('/api/v1/admin/books/?min_rating=4.0')
        assert res_rating.status_code == status.HTTP_200_OK
        items_rating = res_rating.json() if isinstance(res_rating.json(), list) else res_rating.json().get('results', [])
        assert any(b['id'] == self.book1.id for b in items_rating)
        assert not any(b['id'] == self.book2.id for b in items_rating)

        # 2. Modificación de libro (PATCH)
        res_patch = self.client.patch(
            f'/api/v1/admin/books/{self.book1.id}/',
            {
                'title': 'Cien años de soledad (Edición Especial Ilustrada)',
                'description': 'Una de las cumbres de la literatura universal.',
                'category_ids': [self.category_fic.id],
            },
            format='json',
        )
        assert res_patch.status_code == status.HTTP_200_OK
        self.book1.refresh_from_db()
        assert self.book1.title == 'Cien años de soledad (Edición Especial Ilustrada)'
        assert self.book1.description == 'Una de las cumbres de la literatura universal.'
        assert list(self.book1.categories.values_list('id', flat=True)) == [self.category_fic.id]

        # 3. Creación de libro (POST)
        res_create = self.client.post(
            '/api/v1/admin/books/',
            {
                'title': 'El amor en los tiempos del cólera',
                'author_id': self.author.id,
                'isbn': '9780307389732',
                'published_date': '1985-12-05',
                'category_ids': [self.category_fic.id],
            },
            format='json',
        )
        assert res_create.status_code == status.HTTP_201_CREATED
        new_book_id = res_create.json()['id']
        assert Book.objects.filter(id=new_book_id).exists()

    def test_api_admin_author_filtering_and_editing(self):
        self.client.force_authenticate(user=self.admin_user)

        # 1. Modificación de autor
        res_patch = self.client.patch(
            f'/api/v1/admin/authors/{self.author.id}/',
            {
                'name': 'Gabriel José de la Concordia García Márquez',
                'biography': 'Premio Nobel de Literatura en 1982.',
            },
            format='json',
        )
        assert res_patch.status_code == status.HTTP_200_OK
        self.author.refresh_from_db()
        assert self.author.name == 'Gabriel José de la Concordia García Márquez'
        assert self.author.biography == 'Premio Nobel de Literatura en 1982.'

        # 2. Creación de autor
        res_create = self.client.post(
            '/api/v1/admin/authors/',
            {
                'name': 'Mario Vargas Llosa',
                'biography': 'Escritor hispanoperuano galardonado con el Nobel de Literatura.',
            },
            format='json',
        )
        assert res_create.status_code == status.HTTP_201_CREATED
        assert Author.objects.filter(name='Mario Vargas Llosa').exists()

    def test_api_admin_bulk_actions(self):
        self.client.force_authenticate(user=self.admin_user)

        # 1. Bulk action sobre libros: re_enrich
        res_bulk_enrich = self.client.post(
            '/api/v1/admin/books/bulk-action/',
            {
                'action': 're_enrich',
                'book_ids': [self.book1.id, self.book2.id],
            },
            format='json',
        )
        assert res_bulk_enrich.status_code == status.HTTP_200_OK
        assert res_bulk_enrich.json()['processed'] == 2

        # 2. Bulk action sobre libros: delete
        temp_book = Book.objects.create(title='Libro Temporal a Eliminar')
        res_bulk_del = self.client.post(
            '/api/v1/admin/books/bulk-action/',
            {
                'action': 'delete',
                'book_ids': [temp_book.id],
            },
            format='json',
        )
        assert res_bulk_del.status_code == status.HTTP_200_OK
        assert not Book.objects.filter(id=temp_book.id).exists()

        # 3. Bulk action sobre autores: delete
        temp_author = Author.objects.create(name='Autor Temporal a Eliminar')
        res_author_bulk_del = self.client.post(
            '/api/v1/admin/authors/bulk-action/',
            {
                'action': 'delete',
                'author_ids': [temp_author.id],
            },
            format='json',
        )
        assert res_author_bulk_del.status_code == status.HTTP_200_OK
        assert not Author.objects.filter(id=temp_author.id).exists()

    def test_api_categories_list(self):
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get('/api/v1/admin/categories/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        cats = data if isinstance(data, list) else data.get('results', [])
        slugs = [c['slug'] for c in cats]
        assert 'ficcion' in slugs
        assert 'clasicos' in slugs

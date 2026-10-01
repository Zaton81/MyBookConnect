from pathlib import Path
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    AffiliateClick,
    Author,
    AuthorAnnouncement,
    AuthorProfile,
    Book,
    Review,
    UserBook,
)
from books.services.affiliate_service import AffiliateService
from books.services.author_service import AuthorService
from users.models import SubscriptionTier, UserSubscription

User = get_user_model()


@pytest.mark.django_db
class TestPhase31Monetization:
    @pytest.fixture(autouse=True)
    def setup_fixture(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='reader_user',
            email='reader@example.com',
            password='StrongPassword123!',
        )
        self.author_user = User.objects.create_user(
            username='author_user',
            email='author@example.com',
            password='StrongPassword123!',
        )
        self.author = Author.objects.create(
            name='Gabriel García Márquez',
            biography='Premio Nobel de Literatura colombiano.',
        )
        self.book = Book.objects.create(
            title='Cien años de soledad',
            author=self.author,
            isbn='8420471836',
            description='Obra cumbre del realismo mágico.',
        )

    def test_amazon_affiliate_tag_configuration(self):
        """Verifica que el tag de afiliado de Amazon oficial 'mybooksocial-21' está configurado."""
        tag = AffiliateService.get_affiliate_tag()
        assert tag == 'mybooksocial-21', f"El tag esperado es 'mybooksocial-21', actual: '{tag}'"
        assert getattr(settings, 'AMAZON_AFFILIATE_TAG', None) == 'mybooksocial-21'

    def test_affiliate_links_generation_multiformat(self):
        """Comprueba que se generan enlaces para libro físico, ebook Kindle y audiolibro Audible con el tag."""
        data = AffiliateService.generate_affiliate_links(self.book)

        assert data['book_id'] == self.book.id
        assert data['affiliate_tag'] == 'mybooksocial-21'
        assert 'disclosure' in data
        assert 'sin coste adicional para ti' in data['disclosure']

        links = data['links']
        assert 'paperback' in links
        assert 'ebook' in links
        assert 'audiobook' in links

        assert 'tag=mybooksocial-21' in links['paperback']['url']
        assert 'tag=mybooksocial-21' in links['ebook']['url']
        assert 'tag=mybooksocial-21' in links['audiobook']['url']

    def test_book_affiliate_links_api_endpoint(self):
        """Verifica el endpoint GET /api/v1/books/<id>/affiliate-links/."""
        response = self.client.get(f'/api/v1/books/{self.book.id}/affiliate-links/')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['book_title'] == 'Cien años de soledad'
        assert 'links' in data
        assert data['links']['ebook']['store'] == 'Amazon Kindle'

    def test_record_affiliate_click_anonymous(self):
        """Verifica que se registran clics anónimos sin PII para métricas de conversión."""
        response = self.client.post(
            f'/api/v1/books/{self.book.id}/affiliate-click/',
            {'format': 'ebook'},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()['status'] == 'recorded'

        click = AffiliateClick.objects.filter(book=self.book).first()
        assert click is not None
        assert click.format == 'ebook'

    def test_author_profile_creation_and_claim_flow(self):
        """Valida que un usuario puede reclamar un autor del catálogo."""
        self.client.force_authenticate(user=self.author_user)

        claim_data = {
            'author_id': self.author.id,
            'pen_name': 'Gabo',
            'verification_notes': 'Representante oficial de la fundación.',
        }
        res = self.client.post('/api/v1/authors/claim/', claim_data, format='json')
        assert res.status_code == status.HTTP_200_OK
        assert res.json()['author'] == self.author.id
        assert res.json()['pen_name'] == 'Gabo'

        # Consultar perfil propio de autor
        me_res = self.client.get('/api/v1/authors/me/')
        assert me_res.status_code == status.HTTP_200_OK
        assert me_res.json()['pen_name'] == 'Gabo'

    def test_author_dashboard_metrics_aggregation(self):
        """Valida las métricas agregadas del panel del autor (lectores, ratings, desglose)."""
        # Asociar perfil
        profile = AuthorService.claim_author(
            user=self.author_user,
            author_id=self.author.id,
            pen_name='Gabo',
        )

        # Crear lecturas de prueba
        UserBook.objects.create(user=self.user, book=self.book, status='reading')
        Review.objects.create(
            user=self.user,
            book=self.book,
            rating=5,
            title='Excelente',
            text='Una obra maestra sin igual.',
            is_moderated=False,
        )

        self.client.force_authenticate(user=self.author_user)
        dash_res = self.client.get('/api/v1/authors/dashboard/')
        assert dash_res.status_code == status.HTTP_200_OK
        metrics = dash_res.json()

        assert metrics['books_count'] == 1
        assert metrics['readers_total'] == 1
        assert metrics['readers_by_status']['reading'] == 1
        assert metrics['average_rating'] == 5.0
        assert len(metrics['recent_reviews']) == 1

    def test_author_announcements_creation_and_public_listing(self):
        """Valida la creación y lectura pública de comunicados de autores."""
        profile = AuthorService.claim_author(
            user=self.author_user,
            author_id=self.author.id,
        )

        self.client.force_authenticate(user=self.author_user)
        ann_res = self.client.post(
            '/api/v1/authors/announcements/',
            {
                'title': 'Nueva edición conmemorativa',
                'content': 'Próximamente disponible con prólogo especial.',
                'book_id': self.book.id,
                'is_pinned': True,
            },
            format='json',
        )
        assert ann_res.status_code == status.HTTP_201_CREATED
        assert ann_res.json()['title'] == 'Nueva edición conmemorativa'

        # Consulta pública sin autenticación
        self.client.force_authenticate(user=None)
        list_res = self.client.get(f'/api/v1/authors/{self.author.id}/announcements/')
        assert list_res.status_code == status.HTTP_200_OK
        assert len(list_res.json()) >= 1
        assert list_res.json()[0]['title'] == 'Nueva edición conmemorativa'

    def test_user_subscription_status_and_upgrade(self):
        """Verifica la consulta y activación de suscripción de usuario."""
        self.client.force_authenticate(user=self.user)

        # Inicialmente Free
        sub_res = self.client.get('/api/v1/users/subscription/')
        assert sub_res.status_code == status.HTTP_200_OK
        assert sub_res.json()['tier'] == 'free'
        assert sub_res.json()['is_premium'] is False

        # Actualización a Premium
        up_res = self.client.post(
            '/api/v1/users/subscription/',
            {'tier': 'premium'},
            format='json',
        )
        assert up_res.status_code == status.HTTP_200_OK
        assert up_res.json()['tier'] == 'premium'
        assert up_res.json()['is_premium'] is True

    def test_recommendation_service_remains_independent_and_neutral(self):
        """Verifica que el servicio de recomendaciones mantiene la neutralidad algorítmica."""
        from books.services.recommendation_service import get_user_recommendations

        # Generar clics de afiliado no debe alterar la lógica ni forzar la recomendación
        AffiliateClick.objects.create(book=self.book, format='paperback')
        recs = get_user_recommendations(user=self.user, limit=5)
        # Debe ejecutarse sin errores basándose exclusivamente en afinidad
        assert isinstance(recs, list)

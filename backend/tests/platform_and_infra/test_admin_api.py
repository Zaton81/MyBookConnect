import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Errata, ErrataStatus, ErrataType, LegalDocument

User = get_user_model()


@pytest.mark.django_db
class TestAdminAPI:
    def setup_method(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            email='admin@example.com',
            password='Password123!',
            is_staff=True,
            is_superuser=True,
        )
        self.regular_user = User.objects.create_user(
            username='regular_joe',
            email='joe@example.com',
            password='Password123!',
        )

    def test_admin_stats_permission(self):
        # Regular user denied
        self.client.force_authenticate(user=self.regular_user)
        res = self.client.get('/api/v1/admin/stats/')
        assert res.status_code == status.HTTP_403_FORBIDDEN

        # Staff/superuser allowed
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get('/api/v1/admin/stats/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert 'users' in data
        assert 'catalog' in data
        assert 'erratas' in data
        assert data['users']['total'] >= 2

    def test_admin_users_ban_and_protect_self(self):
        self.client.force_authenticate(user=self.admin_user)

        # Ban regular user
        res = self.client.patch(
            f'/api/v1/admin/users/{self.regular_user.id}/',
            {'is_active': False},
            format='json'
        )
        assert res.status_code == status.HTTP_200_OK
        self.regular_user.refresh_from_db()
        assert self.regular_user.is_active is False

        # Attempt to ban self -> validation error
        res_self = self.client.patch(
            f'/api/v1/admin/users/{self.admin_user.id}/',
            {'is_active': False},
            format='json'
        )
        assert res_self.status_code == status.HTTP_400_BAD_REQUEST
        self.admin_user.refresh_from_db()
        assert self.admin_user.is_active is True

    def test_admin_errata_resolution(self):
        errata = Errata.objects.create(
            user=self.regular_user,
            type=ErrataType.ERRATA,
            text='Typo in chapter 1 title',
            status=ErrataStatus.OPEN,
        )

        self.client.force_authenticate(user=self.admin_user)
        res = self.client.patch(
            f'/api/v1/admin/erratas/{errata.id}/',
            {'status': ErrataStatus.APPROVED, 'resolution_notes': 'Corregido en catálogo'},
            format='json'
        )
        assert res.status_code == status.HTTP_200_OK
        errata.refresh_from_db()
        assert errata.status == ErrataStatus.APPROVED
        assert errata.resolution_notes == 'Corregido en catálogo'
        assert errata.editor == self.admin_user

    def test_admin_legal_cms_and_public_view(self):
        self.client.force_authenticate(user=self.admin_user)

        # Create or update Terms of service
        res = self.client.post(
            '/api/v1/admin/legal/',
            {
                'slug': 'terms',
                'title': 'Términos del Servicio Oficiales',
                'content': '# Términos y Condiciones\n\nBienvenido a MyBookConnect.'
            },
            format='json'
        )
        assert res.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]

        doc = LegalDocument.objects.get(slug='terms')
        assert doc.updated_by == self.admin_user

        # Public access without auth
        anon_client = APIClient()
        pub_res = anon_client.get('/api/v1/books/legal/terms/')
        assert pub_res.status_code == status.HTTP_200_OK
        assert pub_res.json()['title'] == 'Términos del Servicio Oficiales'

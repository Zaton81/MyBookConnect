from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.cache_utils import invalidate_trending_cache, trending_key
from books.models import Author, Book, Review, UserBook
from books.services.trending_service import get_trending_books
from books.tasks import precompute_trending_task

User = get_user_model()


@pytest.mark.django_db
class TestPhase23Trending:
    """Suite de pruebas para la Fase 23: Ranking de Tendencias con Decaimiento Temporal."""

    @pytest.fixture
    def test_user(self):
        return User.objects.create_user(
            username='trend_tester',
            email='trend@example.com',
            password='Password123!',
        )

    @pytest.fixture
    def sample_books(self):
        author = Author.objects.create(name='Brandon Sanderson')
        b_recent = Book.objects.create(title='Viento y Verdad', author=author, isbn='9788466657661')
        b_old = Book.objects.create(title='El Aliento de los Dioses', author=author, isbn='9788466657662')
        return b_recent, b_old

    def test_trending_score_with_temporal_decay(self, test_user, sample_books):
        b_recent, b_old = sample_books
        invalidate_trending_cache()

        now = timezone.now()

        # Actividad reciente (hace 2 días) en b_recent
        u2 = User.objects.create_user(username='u2', email='u2@test.com', password='pwd')
        u3 = User.objects.create_user(username='u3', email='u3@test.com', password='pwd')

        with patch('django.utils.timezone.now', return_value=now - timedelta(days=2)):
            r1 = Review.objects.create(user=test_user, book=b_recent, rating=10, text='¡Genial!')
            r1.created_at = now - timedelta(days=2)
            r1.save()

            r2 = Review.objects.create(user=u2, book=b_recent, rating=9, text='Increíble')
            r2.created_at = now - timedelta(days=2)
            r2.save()

            ub1 = UserBook.objects.create(user=u3, book=b_recent, is_read=True)
            ub1.updated_at = now - timedelta(days=2)
            ub1.save()

        # Actividad antigua (hace 45 días) en b_old
        u4 = User.objects.create_user(username='u4', email='u4@test.com', password='pwd')
        u5 = User.objects.create_user(username='u5', email='u5@test.com', password='pwd')

        with patch('django.utils.timezone.now', return_value=now - timedelta(days=45)):
            r3 = Review.objects.create(user=u4, book=b_old, rating=10, text='Antiguo favorito')
            r3.created_at = now - timedelta(days=45)
            r3.save()

            r4 = Review.objects.create(user=u5, book=b_old, rating=10, text='Muy bueno')
            r4.created_at = now - timedelta(days=45)
            r4.save()

        # En la ventana 'week' (7 días), b_recent debe superar claramente a b_old
        results_week = get_trending_books(period='week', limit=5)
        assert len(results_week) >= 2
        assert results_week[0]['id'] == b_recent.id
        assert results_week[0]['rank'] == 1
        assert results_week[0]['trending_score'] > results_week[1]['trending_score']

    def test_trending_view_api(self, test_user, sample_books):
        b_recent, _ = sample_books
        invalidate_trending_cache()

        client = APIClient()
        client.force_authenticate(user=test_user)

        # Crear interacción reciente
        Review.objects.create(user=test_user, book=b_recent, rating=9, text='Excelente obra')

        response = client.get('/api/v1/books/trending/?period=week')
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert 'results' in data
        assert data.get('period') == 'week'
        assert len(data['results']) > 0

        first = data['results'][0]
        assert 'rank' in first
        assert 'trending_score' in first
        assert 'title' in first
        assert 'author_name' in first

    def test_trending_cache_and_invalidation(self, test_user, sample_books):
        b_recent, _ = sample_books
        cache.delete(trending_key('week'))
        cache.delete(trending_key('all'))

        # Primer cálculo guarda en caché
        res1 = get_trending_books(period='week', limit=10)
        assert len(res1) >= 0
        assert cache.get(trending_key('week')) is not None

        # Invalidate trending cache limpia todos los periodos
        invalidate_trending_cache()
        assert cache.get(trending_key('week')) is None
        assert cache.get(trending_key('all')) is None

    def test_precompute_trending_task(self):
        invalidate_trending_cache()
        summary = precompute_trending_task()
        assert 'week' in summary
        assert 'month' in summary
        assert 'year' in summary
        assert 'all' in summary
        # Todos los periodos deben quedar cacheados
        assert cache.get(trending_key('week')) is not None
        assert cache.get(trending_key('month')) is not None

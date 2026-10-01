from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.models import ProductAnalyticsEvent, ProductEventType
from analytics.services import AnalyticsService, hash_ip_address
from analytics.tasks import record_analytics_event_task
from books.models import Author, Book

User = get_user_model()


@pytest.mark.django_db
class TestPhase26ProductAnalytics:
    def setup_method(self):
        self.user = User.objects.create_user(
            username='lector_analytics', email='analytics@test.com', password='password123'
        )
        self.staff_user = User.objects.create_user(
            username='staff_analytics', email='staff@test.com', password='password123', is_staff=True
        )
        self.author = Author.objects.create(name='Italo Calvino')
        self.book = Book.objects.create(title='Las ciudades invisibles', author=self.author)
        self.client = APIClient()

    # ─── 1. Definición y Registro de los 13 Eventos Canónicos ───

    def test_all_13_canonical_events_can_be_tracked(self):
        """Verifica que los 13 eventos del Roadmap se puedan registrar correctamente."""
        all_event_types = [
            ProductEventType.SIGNUP,
            ProductEventType.LOGIN,
            ProductEventType.BOOK_VIEW,
            ProductEventType.BOOK_ADDED,
            ProductEventType.READING_STARTED,
            ProductEventType.READING_FINISHED,
            ProductEventType.REVIEW_CREATED,
            ProductEventType.FOLLOW_CREATED,
            ProductEventType.LIST_CREATED,
            ProductEventType.RECOMMENDATION_SHOWN,
            ProductEventType.RECOMMENDATION_CLICKED,
            ProductEventType.RECOMMENDATION_DISMISSED,
            ProductEventType.MESSAGE_SENT,
        ]
        assert len(all_event_types) == 13

        for ev_type in all_event_types:
            ev = AnalyticsService.track_event(
                event_type=ev_type,
                user=self.user,
                metadata={'book_id': self.book.id},
            )
            assert ev.id is not None
            assert ev.event_type == ev_type
            assert ev.user == self.user

        assert ProductAnalyticsEvent.objects.count() == 13

    # ─── 2. Privacidad por Diseño y Sanitización ───

    def test_privacy_and_metadata_sanitization(self):
        """Asegura que claves sensibles (password, token, etc.) sean descartadas y la IP sea anonimizada."""
        ev = AnalyticsService.track_event(
            event_type=ProductEventType.LOGIN,
            user=self.user,
            metadata={
                'source': 'web',
                'password': 'secret_password_123',
                'token': 'bearer_token_xyz',
                'book_id': self.book.id,
            },
        )

        assert 'password' not in ev.metadata
        assert 'token' not in ev.metadata
        assert ev.metadata['source'] == 'web'
        assert ev.metadata['book_id'] == self.book.id

    def test_ip_address_is_hashed_and_disassociated(self):
        """Verifica que la función hash_ip_address devuelva un hash truncado sin revelar la IP."""
        h1 = hash_ip_address('198.51.100.45')
        assert len(h1) == 16
        assert '198' not in h1
        # Determinismo
        assert hash_ip_address('198.51.100.45') == h1

    def test_user_deletion_anonymizes_events_gracefully(self):
        """Verifica que al eliminar un usuario, los eventos pasen a user=None (SET_NULL) sin perder métricas."""
        temp_user = User.objects.create_user(username='temp_user', email='temp@test.com', password='pwd')
        ev = AnalyticsService.track_event(event_type=ProductEventType.BOOK_VIEW, user=temp_user)

        assert ev.user == temp_user
        temp_user.delete()

        ev.refresh_from_db()
        assert ev.user is None

    # ─── 3. Embudo de Conversión y Ciclo de Vida (Funnel) ───

    def test_funnel_metrics_calculation(self):
        """Verifica el cálculo de las etapas del embudo: visit -> signup -> activation -> reading."""
        # 1. Visita anónima
        AnalyticsService.track_event(
            event_type=ProductEventType.BOOK_VIEW,
            session_id='anon_session_1',
            metadata={'book_id': self.book.id},
        )
        # 2. Signup
        AnalyticsService.track_event(
            event_type=ProductEventType.SIGNUP,
            user=self.user,
        )
        # 3. Activación (añadir libro)
        AnalyticsService.track_event(
            event_type=ProductEventType.BOOK_ADDED,
            user=self.user,
            metadata={'book_id': self.book.id},
        )
        # 4. Lectura terminada
        AnalyticsService.track_event(
            event_type=ProductEventType.READING_FINISHED,
            user=self.user,
            metadata={'book_id': self.book.id},
        )

        funnel = AnalyticsService.get_funnel_metrics()
        steps = funnel['funnel_steps']
        rates = funnel['conversion_rates']

        assert steps['visits'] >= 1
        assert steps['signups'] >= 1
        assert steps['activations'] >= 1
        assert steps['reading_completed'] >= 1
        assert 'signup_to_activation_pct' in rates

    # ─── 4. Tarea Celery Asíncrona ───

    def test_celery_record_analytics_event_task(self):
        """Verifica la ejecución en segundo plano mediante Celery."""
        success = record_analytics_event_task(
            event_type=ProductEventType.MESSAGE_SENT,
            user_id=self.user.id,
            metadata={'recipient_id': 99},
        )
        assert success is True
        assert ProductAnalyticsEvent.objects.filter(event_type=ProductEventType.MESSAGE_SENT).exists()

    # ─── 5. Endpoint de Ingesta (Collect API) ───

    def test_collect_endpoint_authenticated_and_anonymous(self):
        """Verifica el endpoint POST /api/v1/analytics/collect/."""
        # Petición anónima
        res_anon = self.client.post(
            "/api/v1/analytics/collect/",
            {
                'event_type': 'book_view',
                'session_id': 'sess_guest_999',
                'metadata': {'book_id': self.book.id},
            },
            format='json',
        )
        assert res_anon.status_code == 201

        # Petición autenticada
        self.client.force_authenticate(user=self.user)
        res_auth = self.client.post(
            "/api/v1/analytics/collect/",
            {
                'event_type': 'recommendation_clicked',
                'metadata': {'recommendation_id': 42},
            },
            format='json',
        )
        assert res_auth.status_code == 201

    def test_collect_endpoint_rejects_invalid_event_type(self):
        """Rechaza eventos con nombres no soportados."""
        res = self.client.post(
            "/api/v1/analytics/collect/",
            {'event_type': 'evento_falso_invalido'},
            format='json',
        )
        assert res.status_code == 400

    def test_collect_endpoint_async_mode(self):
        """Verifica que el parámetro async_mode encole la tarea Celery y devuelva 202."""
        with patch("analytics.tasks.record_analytics_event_task.delay") as mock_delay:
            res = self.client.post(
                "/api/v1/analytics/collect/",
                {
                    'event_type': 'book_view',
                    'async_mode': True,
                },
                format='json',
            )
            assert res.status_code == 202
            mock_delay.assert_called_once()

    # ─── 6. Endpoints de Métricas de Administración ───

    def test_admin_funnel_and_summary_endpoints_permission_check(self):
        """Los endpoints de embudo y resumen requieren permisos de staff."""
        url_funnel = "/api/v1/analytics/funnel/"
        url_summary = "/api/v1/analytics/summary/"

        # No autenticado: 401
        assert self.client.get(url_funnel).status_code == 401
        assert self.client.get(url_summary).status_code == 401

        # Usuario normal no-staff: 403
        self.client.force_authenticate(user=self.user)
        assert self.client.get(url_funnel).status_code == 403
        assert self.client.get(url_summary).status_code == 403

        # Usuario staff: 200
        self.client.force_authenticate(user=self.staff_user)
        res_f = self.client.get(url_funnel)
        assert res_f.status_code == 200
        assert "funnel_steps" in res_f.json()

        res_s = self.client.get(url_summary)
        assert res_s.status_code == 200
        assert "events_by_type" in res_s.json()

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, RecommendationFeedback, RecommendationFeedbackAction
from books.services.recommendation_feedback_service import (
    get_recommendation_metrics,
    record_recommendation_event,
)

User = get_user_model()


@pytest.mark.django_db
class TestPhase25RecommendationFeedback:
    def setup_method(self):
        self.user = User.objects.create_user(username='lector_test', email='lector@test.com', password='pwd')
        self.author = Author.objects.create(name='Gabriel García Márquez')
        self.book1 = Book.objects.create(title='Cien años de soledad', author=self.author, average_rating=4.9)
        self.book2 = Book.objects.create(title='El coronel no tiene quien le escriba', author=self.author, average_rating=4.5)
        self.client = APIClient()

    def test_record_feedback_service_valid(self):
        """Verifica el registro exitoso de eventos de recomendación válidos."""
        fb = record_recommendation_event(
            user=self.user,
            book_id=self.book1.id,
            action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN,
            recommendation_id='rec_abc123',
            strategy='hybrid',
            algorithm_version='v1.0',
            metadata={'position': 1, 'score': 0.95},
        )
        assert fb.id is not None
        assert fb.user == self.user
        assert fb.book == self.book1
        assert fb.action == RecommendationFeedbackAction.RECOMMENDATION_SHOWN
        assert fb.strategy == 'hybrid'
        assert fb.metadata.get('position') == 1

    def test_record_feedback_service_invalid_action(self):
        """Verifica que una acción desconocida lance ValueError."""
        with pytest.raises(ValueError, match="Acción 'accion_inexistente' inválida"):
            record_recommendation_event(
                user=self.user,
                book_id=self.book1.id,
                action='accion_inexistente',
            )

    def test_record_feedback_service_invalid_book(self):
        """Verifica que un book_id inexistente lance ValueError."""
        with pytest.raises(ValueError, match="Libro con id=999999 no encontrado"):
            record_recommendation_event(
                user=self.user,
                book_id=999999,
                action=RecommendationFeedbackAction.RECOMMENDATION_CLICKED,
            )

    def test_metrics_calculation(self):
        """Verifica el cálculo de métricas de CTR y tasas de conversión."""
        # 10 impresiones
        for _ in range(10):
            record_recommendation_event(
                user=self.user,
                book_id=self.book1.id,
                action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN,
                strategy='hybrid',
            )
        # 2 clicks -> CTR = 20%
        for _ in range(2):
            record_recommendation_event(
                user=self.user,
                book_id=self.book1.id,
                action=RecommendationFeedbackAction.RECOMMENDATION_CLICKED,
                strategy='hybrid',
            )
        # 1 wishlist -> 10%
        record_recommendation_event(
            user=self.user,
            book_id=self.book1.id,
            action=RecommendationFeedbackAction.WISHLIST_ADDED,
            strategy='hybrid',
        )
        # 2 inicios de lectura y 1 finalización -> start rate 20%, completion 50%
        record_recommendation_event(
            user=self.user,
            book_id=self.book1.id,
            action=RecommendationFeedbackAction.READING_STARTED,
            strategy='hybrid',
        )
        record_recommendation_event(
            user=self.user,
            book_id=self.book1.id,
            action=RecommendationFeedbackAction.READING_STARTED,
            strategy='hybrid',
        )
        record_recommendation_event(
            user=self.user,
            book_id=self.book1.id,
            action=RecommendationFeedbackAction.READING_FINISHED,
            strategy='hybrid',
        )

        metrics = get_recommendation_metrics()
        assert metrics['totals']['shown'] == 10
        assert metrics['totals']['clicked'] == 2
        assert metrics['totals']['wishlist_added'] == 1
        assert metrics['totals']['reading_started'] == 2
        assert metrics['totals']['reading_finished'] == 1
        assert metrics['kpis']['ctr'] == 20.0
        assert metrics['kpis']['wishlist_rate'] == 10.0
        assert metrics['kpis']['start_rate'] == 20.0
        assert metrics['kpis']['completion_rate'] == 50.0

        assert len(metrics['by_strategy']) == 1
        assert metrics['by_strategy'][0]['strategy'] == 'hybrid'
        assert metrics['by_strategy'][0]['ctr'] == 20.0

    def test_api_feedback_create_single_and_batch(self):
        """Verifica los endpoints REST para registrar eventos individuales y por lotes."""
        self.client.force_authenticate(user=self.user)

        # Evento individual
        response = self.client.post('/api/v1/books/recommendations/feedback/', {
            'book_id': self.book1.id,
            'action': RecommendationFeedbackAction.RECOMMENDATION_CLICKED,
            'strategy': 'social',
            'algorithm_version': 'v1.0',
        }, format='json')

        assert response.status_code == 201
        assert response.data['count'] == 1
        assert RecommendationFeedback.objects.filter(action=RecommendationFeedbackAction.RECOMMENDATION_CLICKED).count() == 1

        # Evento por lotes (ej: registrar impresiones de 2 libros mostrados a la vez)
        batch_data = [
            {
                'book_id': self.book1.id,
                'action': RecommendationFeedbackAction.RECOMMENDATION_SHOWN,
                'strategy': 'social',
            },
            {
                'book_id': self.book2.id,
                'action': RecommendationFeedbackAction.RECOMMENDATION_SHOWN,
                'strategy': 'social',
            },
        ]
        response_batch = self.client.post('/api/v1/books/recommendations/feedback/', batch_data, format='json')
        assert response_batch.status_code == 201
        assert response_batch.data['count'] == 2
        assert RecommendationFeedback.objects.filter(action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN).count() == 2

    def test_api_feedback_unauthenticated(self):
        """Verifica que usuarios anónimos no puedan registrar eventos."""
        response = self.client.post('/api/v1/books/recommendations/feedback/', {
            'book_id': self.book1.id,
            'action': RecommendationFeedbackAction.RECOMMENDATION_CLICKED,
        }, format='json')
        assert response.status_code == 401

    def test_api_metrics_endpoint(self):
        """Verifica que el endpoint de métricas devuelva la estructura completa."""
        self.client.force_authenticate(user=self.user)
        # Crear algún evento
        record_recommendation_event(
            user=self.user,
            book_id=self.book1.id,
            action=RecommendationFeedbackAction.RECOMMENDATION_SHOWN,
        )

        response = self.client.get('/api/v1/books/recommendations/metrics/')
        assert response.status_code == 200
        data = response.data
        assert 'totals' in data
        assert 'kpis' in data
        assert 'by_strategy' in data
        assert 'by_version' in data
        assert data['totals']['shown'] >= 1

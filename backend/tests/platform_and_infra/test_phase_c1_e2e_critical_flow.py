"""
Suite de Pruebas de Flujo E2E Crítico de Ciclo de Vida Completo (Fase C1)
Valida la integración integral de la plataforma My Book Social:
Registro -> Marcar libro en biblioteca -> Publicar Reseña -> Muro / Mensajería -> Feed social.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingStatus, Review, UserBook
from users.models import Activity, ActivityType, UserPost

User = get_user_model()


@pytest.mark.django_db
class TestPhaseC1E2ECriticalFlow:
    """Verifica el flujo E2E crítico de ciclo de vida completo de extremo a extremo."""

    def test_complete_reader_lifecycle_e2e(self):
        client = APIClient()

        # ── 1. Preparar Catálogo Semilla ──
        author = Author.objects.create(name="Gabriel García Márquez")
        category = Category.objects.create(name="Realismo Mágico", slug="realismo-magico")
        book = Book.objects.create(
            title="Cien años de soledad",
            author=author,
            isbn="9780307474728",
            description="La historia de la familia Buendía en Macondo.",
        )
        book.categories.add(category)
        book.authors.add(author)

        # Usuario amigo preexistente
        friend = User.objects.create_user(
            username="lector_amigo",
            email="amigo@mybooksocial.com",
            password="SecurePass2026!",
        )

        # ── 2. Registro de Usuario e Inicio de Sesión ──
        register_payload = {
            "username": "nuevo_lector",
            "email": "nuevo@mybooksocial.com",
            "password": "PasswordSegura123!",
            "password2": "PasswordSegura123!",
        }
        res_register = client.post('/api/v1/users/register/', register_payload, format='json')
        assert res_register.status_code == status.HTTP_201_CREATED, res_register.data

        # Autenticar con el usuario recién registrado
        user = User.objects.get(username="nuevo_lector")
        client.force_authenticate(user=user)

        # ── 3. Gestión de Biblioteca Personal (UserBook) ──
        # Añadir a la biblioteca como 'READING'
        user_book = UserBook.objects.create(
            user=user,
            book=book,
            status=ReadingStatus.READING,
        )
        assert user_book.status == ReadingStatus.READING

        # Pasar a 'READ' (Leído)
        user_book.status = ReadingStatus.READ
        user_book.save()

        # ── 4. Publicación de Reseña de 5 Estrellas ──
        review_payload = {
            "book": book.id,
            "rating": 5,
            "title": "Una obra maestra absoluta",
            "content": "Narrativa incomparable y personajes inolvidables.",
        }
        res_review = client.post('/api/v1/books/reviews/', review_payload, format='json')
        assert res_review.status_code == status.HTTP_201_CREATED, res_review.data
        review_id = res_review.data['id']
        assert res_review.data['rating'] == 5

        # Verificar recálculo atómico de calificación en el libro
        book.refresh_from_db()
        assert book.average_rating == 5.0

        # ── 5. Interacción Social: Seguir a amigo y Publicar en su Muro ──
        user.following.add(friend)

        post_payload = {
            "content": "¡Hola amigo! Acabo de terminar Cien años de soledad, te lo recomiendo muchísimo.",
            "book": book.id,
        }
        res_post = client.post(f'/api/v1/users/{friend.id}/posts/', post_payload, format='json')
        assert res_post.status_code == status.HTTP_201_CREATED, res_post.data

        # ── 6. Generación de Ticket Seguro para WebSockets de Chat ──
        res_ticket = client.post('/api/v1/auth/ws-ticket/')
        assert res_ticket.status_code == status.HTTP_200_OK
        assert 'ticket' in res_ticket.data
        assert len(res_ticket.data['ticket']) > 20

        # ── 7. Consulta del Feed Social y Consistencia de Actividades ──
        # Registrar una actividad para el feed
        Activity.objects.create(
            user=user,
            type=ActivityType.BOOK_FINISHED,
            book=book,
        )

        res_feed = client.get('/api/v1/users/feed/')
        assert res_feed.status_code == status.HTTP_200_OK
        # Verificar que el feed no arroja errores y contiene la actividad
        results = res_feed.data.get('results', res_feed.data)
        assert len(results) >= 1

        # ── 8. Verificación del Perfil Público y Privacidad ──
        res_profile = client.get(f'/api/v1/users/{user.id}/')
        assert res_profile.status_code == status.HTTP_200_OK
        assert res_profile.data['username'] == "nuevo_lector"

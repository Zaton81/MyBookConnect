import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Review, ReviewComment
from messages_app.models import Conversation, Message

User = get_user_model()


@pytest.fixture
def user1(db):
    return User.objects.create_user(username='user1', email='user1@example.com', password='password123')


@pytest.fixture
def user2(db):
    return User.objects.create_user(username='user2', email='user2@example.com', password='password123')


@pytest.fixture
def author(db):
    return Author.objects.create(name='Julio Cortázar')


@pytest.fixture
def book(db, author):
    return Book.objects.create(title='Rayuela', author=author, isbn='9788437604572')


@pytest.fixture
def client_for():
    def _make_client(user):
        c = APIClient()
        if user:
            c.force_authenticate(user=user)
        return c
    return _make_client


@pytest.mark.django_db
class TestCoherentBooksEndpoints:
    """Verifica las rutas canónicas del recurso Books."""

    def test_books_list_and_detail(self, client_for, user1, book):
        client = client_for(user1)
        res_list = client.get('/api/v1/books/')
        assert res_list.status_code == status.HTTP_200_OK

        res_detail = client.get(f'/api/v1/books/{book.id}/')
        assert res_detail.status_code == status.HTTP_200_OK
        assert res_detail.data['id'] == book.id
        assert res_detail.data['title'] == 'Rayuela'

    def test_books_recommendations(self, client_for, user1, book):
        client = client_for(user1)
        res = client.get(f'/api/v1/books/{book.id}/recommendations/')
        assert res.status_code == status.HTTP_200_OK

    def test_books_import_validation(self, client_for, user1):
        client = client_for(user1)
        res = client.post('/api/v1/books/import/', {})
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCoherentUsersEndpoints:
    """Verifica las rutas canónicas del recurso Users y acciones de seguimiento."""

    def test_users_detail_and_follow_actions(self, client_for, user1, user2):
        client = client_for(user1)

        # Detalle de usuario
        res_user = client.get(f'/api/v1/users/{user2.id}/')
        assert res_user.status_code == status.HTTP_200_OK
        assert res_user.data['id'] == user2.id

        # Seguir usuario: POST /api/v1/users/{id}/follow/
        res_follow = client.post(f'/api/v1/users/{user2.id}/follow/')
        assert res_follow.status_code == status.HTTP_200_OK
        assert user1.following.filter(id=user2.id).exists()

        # Dejar de seguir: POST /api/v1/users/{id}/unfollow/
        res_unfollow = client.post(f'/api/v1/users/{user2.id}/unfollow/')
        assert res_unfollow.status_code == status.HTTP_200_OK
        assert not user1.following.filter(id=user2.id).exists()


@pytest.mark.django_db
class TestCoherentReviewsEndpoints:
    """Verifica las rutas canónicas del recurso Reviews (/api/v1/reviews/)."""

    def test_reviews_crud_and_interactions(self, client_for, user1, user2, book):
        client = client_for(user1)

        # 1. Crear reseña: POST /api/v1/reviews/
        res_create = client.post('/api/v1/reviews/', {
            'book_id': book.id,
            'rating': 5,
            'title': 'Maravilla',
            'text': 'Una obra experimental fascinante',
        })
        assert res_create.status_code == status.HTTP_201_CREATED
        review_id = res_create.data['id']

        # 2. Listar reseñas: GET /api/v1/reviews/?book={id}
        res_list = client.get(f'/api/v1/reviews/?book={book.id}')
        assert res_list.status_code == status.HTTP_200_OK
        results = res_list.data.get('results', res_list.data)
        assert any(r['id'] == review_id for r in results)

        # 3. Detalle de reseña: GET /api/v1/reviews/{id}/
        res_detail = client.get(f'/api/v1/reviews/{review_id}/')
        assert res_detail.status_code == status.HTTP_200_OK
        assert res_detail.data['title'] == 'Maravilla'

        # 4. Like en reseña: POST /api/v1/reviews/{id}/like/
        client2 = client_for(user2)
        res_like = client2.post(f'/api/v1/reviews/{review_id}/like/')
        assert res_like.status_code == status.HTTP_200_OK
        assert res_like.data['liked'] is True

        # 5. Comentarios en reseña: POST /api/v1/reviews/{id}/comments/ y GET
        res_comm = client2.post(f'/api/v1/reviews/{review_id}/comments/', {
            'content': 'Totalmente de acuerdo',
        })
        assert res_comm.status_code == status.HTTP_201_CREATED
        comment_id = res_comm.data['id']

        res_comm_list = client.get(f'/api/v1/reviews/{review_id}/comments/')
        assert res_comm_list.status_code == status.HTTP_200_OK
        comm_items = res_comm_list.data if isinstance(res_comm_list.data, list) else res_comm_list.data.get('results', [])
        assert any(c['id'] == comment_id for c in comm_items)

        # 6. Borrar comentario: DELETE /api/v1/reviews/{id}/comments/{comment_id}/
        res_del_comm = client2.delete(f'/api/v1/reviews/{review_id}/comments/{comment_id}/')
        assert res_del_comm.status_code == status.HTTP_204_NO_CONTENT

        # 7. Borrado lógico de reseña: DELETE /api/v1/reviews/{id}/
        res_del = client.delete(f'/api/v1/reviews/{review_id}/')
        assert res_del.status_code == status.HTTP_204_NO_CONTENT
        assert Review.objects.get(id=review_id).is_deleted


@pytest.mark.django_db
class TestCoherentConversationsAndMessagesEndpoints:
    """Verifica las rutas canónicas /api/v1/conversations/ y /api/v1/messages/."""

    def test_canonical_chat_flow(self, client_for, user1, user2):
        # Permitir chat estableciendo relación de seguimiento
        user1.following.add(user2)

        client1 = client_for(user1)

        # 1. Iniciar conversación: POST /api/v1/conversations/start/
        res_start = client1.post('/api/v1/conversations/start/', {'user_id': user2.id})
        assert res_start.status_code == status.HTTP_200_OK
        conv_id = res_start.data['conversation_id']

        # 2. Listar conversaciones: GET /api/v1/conversations/
        res_convs = client1.get('/api/v1/conversations/')
        assert res_convs.status_code == status.HTTP_200_OK
        items = res_convs.data['results'] if isinstance(res_convs.data, dict) and 'results' in res_convs.data else res_convs.data
        assert any(c['id'] == conv_id for c in items)

        # 3. Detalle de conversación: GET /api/v1/conversations/{id}/
        res_conv_detail = client1.get(f'/api/v1/conversations/{conv_id}/')
        assert res_conv_detail.status_code == status.HTTP_200_OK
        assert res_conv_detail.data['id'] == conv_id

        # 4. Enviar mensaje: POST /api/v1/messages/
        res_msg = client1.post('/api/v1/messages/', {
            'conversation': conv_id,
            'text': 'Hola Julio!',
        })
        assert res_msg.status_code == status.HTTP_201_CREATED
        msg_id = res_msg.data['id']

        # 5. Listar mensajes: GET /api/v1/messages/?conversation={id}
        res_msgs = client1.get(f'/api/v1/messages/?conversation={conv_id}')
        assert res_msgs.status_code == status.HTTP_200_OK
        msg_items = res_msgs.data.get('results', res_msgs.data)
        assert any(m['id'] == msg_id for m in msg_items)

        # 6. Detalle de mensaje: GET /api/v1/messages/{id}/
        res_msg_detail = client1.get(f'/api/v1/messages/{msg_id}/')
        assert res_msg_detail.status_code == status.HTTP_200_OK
        assert res_msg_detail.data['text'] == 'Hola Julio!'


@pytest.mark.django_db
class TestBackwardCompatibilityLegacyRoutes:
    """Asegura que los endpoints históricos sigan funcionando de forma transparente."""

    def test_legacy_reviews_and_chat_routes(self, client_for, user1, book):
        review = Review.objects.create(user=user1, book=book, rating=4, title='Original')

        client = client_for(user1)

        # Legacy /api/v1/books/reviews/?book={id}
        res_legacy_rev = client.get(f'/api/v1/books/reviews/?book={book.id}')
        assert res_legacy_rev.status_code == status.HTTP_200_OK

        # Legacy /api/v1/books/reviews/{id}/
        res_legacy_detail = client.get(f'/api/v1/books/reviews/{review.id}/')
        assert res_legacy_detail.status_code == status.HTTP_200_OK
        assert res_legacy_detail.data['id'] == review.id

        # Legacy /api/v1/chat/conversations/
        res_legacy_chat = client.get('/api/v1/chat/conversations/')
        assert res_legacy_chat.status_code == status.HTTP_200_OK

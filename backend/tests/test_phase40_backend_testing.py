"""
Fase 40: Backend Testing
Suite integral de pruebas unitarias y de integración para validar:
- Seguridad (Aislamiento de UserBook, Review, perfiles privados, usuarios bloqueados y mensajería).
- Integridad (Unicidad y actualización de reviews, normalización de ISBN, rangos de rating, estado y progreso).
- Social (Seguir, dejar de seguir, bloquear, desbloquear y restricciones entre usuarios bloqueados).
- Integración (Importación de libros, resiliencia ante fallos externos, chat directo, pipeline de IA y recomendaciones).
"""
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, ReadingStatus, Review, UserBook
from messages_app.models import Conversation, Message
from users.models import PrivacyChoices

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_users():
    alice = User.objects.create_user(username='alice40', email='alice40@example.com', password='password123')
    bob = User.objects.create_user(username='bob40', email='bob40@example.com', password='password123')
    charlie = User.objects.create_user(username='charlie40', email='charlie40@example.com', password='password123')
    return {'alice': alice, 'bob': bob, 'charlie': charlie}


@pytest.fixture
def sample_book():
    author = Author.objects.create(name='Gabriel García Márquez')
    book = Book.objects.create(
        title='Cien años de soledad',
        author=author,
        isbn='978-84-376-0494-7',
        description='Historia de la familia Buendía en Macondo.'
    )
    return book


# ============================================================================
# 1. SEGURIDAD
# ============================================================================
@pytest.mark.django_db
class TestPhase40Security:
    def test_user_cannot_edit_or_delete_other_user_book(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        bob = test_users['bob']

        # Alice crea su UserBook
        user_book = UserBook.objects.create(
            user=alice,
            book=sample_book,
            status=ReadingStatus.READING,
            progress=40,
            rating=4
        )

        # Bob intenta modificar el UserBook de Alice
        api_client.force_authenticate(user=bob)
        res_patch = api_client.patch(
            f'/api/v1/books/user/books/{user_book.id}/',
            {'progress': 90},
            format='json'
        )
        assert res_patch.status_code in [403, 404]

        # Bob intenta eliminar el UserBook de Alice
        res_delete = api_client.delete(f'/api/v1/books/user/books/{user_book.id}/')
        assert res_delete.status_code in [403, 404]

        # Verificar que el registro de Alice sigue intacto
        user_book.refresh_from_db()
        assert user_book.progress == 40

    def test_user_cannot_edit_or_delete_other_user_review(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        bob = test_users['bob']

        # Alice crea una reseña
        review = Review.objects.create(
            user=alice,
            book=sample_book,
            rating=5,
            title='Gran obra',
            text='Magnífica lectura.'
        )

        # Bob intenta editar la reseña de Alice
        api_client.force_authenticate(user=bob)
        res_patch = api_client.patch(
            f'/api/v1/books/reviews/{review.id}/',
            {'text': 'Texto hackeado por Bob'},
            format='json'
        )
        assert res_patch.status_code == 403

        # Bob intenta borrar la reseña de Alice
        res_delete = api_client.delete(f'/api/v1/books/reviews/{review.id}/')
        assert res_delete.status_code == 403

        review.refresh_from_db()
        assert review.text == 'Magnífica lectura.'

    def test_blocked_user_restrictions(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        bob = test_users['bob']

        # Alice bloquea a Bob
        alice.blocked_users.add(bob)

        # Crear reseña de Alice
        review = Review.objects.create(user=alice, book=sample_book, rating=5, title='Review de Alice')

        api_client.force_authenticate(user=bob)

        # 1. Bob no puede ver el perfil de Alice
        res_profile = api_client.get(f'/api/v1/users/{alice.id}/')
        assert res_profile.status_code == 403

        # 2. Bob no puede seguir a Alice
        res_follow = api_client.post(f'/api/v1/users/{alice.id}/follow/')
        assert res_follow.status_code == 403

        # 3. Bob no puede iniciar chat con Alice
        res_chat = api_client.post('/api/v1/conversations/start/', {'user_id': alice.id}, format='json')
        assert res_chat.status_code == 403

        # 4. Bob no puede dar like a la reseña de Alice
        res_like = api_client.post(f'/api/v1/books/reviews/{review.id}/like/')
        assert res_like.status_code == 403

    def test_private_profile_access_restriction(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        # Alice define su perfil como privado
        alice.privacy_level = PrivacyChoices.PRIVATE
        alice.save()

        # Bob (no es seguidor) intenta ver el perfil
        api_client.force_authenticate(user=bob)
        res = api_client.get(f'/api/v1/users/{alice.id}/')
        assert res.status_code == 403
        assert 'privado' in res.data.get('detail', '').lower()

    def test_unauthorized_conversation_access(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']
        charlie = test_users['charlie']

        # Conversación entre Alice y Bob
        conv, _ = Conversation.get_or_create_direct(alice, bob)
        Message.objects.create(conversation=conv, sender=alice, text='Mensaje secreto')

        # Charlie (tercero no participante) intenta acceder a la conversación
        api_client.force_authenticate(user=charlie)
        res = api_client.get(f'/api/v1/conversations/{conv.id}/')
        assert res.status_code in [403, 404]

    def test_unauthorized_message_sending(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']
        charlie = test_users['charlie']

        conv, _ = Conversation.get_or_create_direct(alice, bob)

        # Charlie intenta enviar un mensaje a la conversación de Alice y Bob
        api_client.force_authenticate(user=charlie)
        res = api_client.post(
            '/api/v1/messages/',
            {'conversation': conv.id, 'text': 'Infiltrado'},
            format='json'
        )
        assert res.status_code in [400, 403, 404]


# ============================================================================
# 2. INTEGRIDAD
# ============================================================================
@pytest.mark.django_db
class TestPhase40Integrity:
    def test_duplicate_active_review_handled_or_updated(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        # Primera review creada
        res1 = api_client.post(
            '/api/v1/books/reviews/',
            {'book_id': sample_book.id, 'rating': 4, 'title': 'Primera', 'text': 'Texto 1'},
            format='json'
        )
        assert res1.status_code in [200, 201]

        # Segunda review para el mismo libro: el endpoint actualiza la existente
        res2 = api_client.post(
            '/api/v1/books/reviews/',
            {'book_id': sample_book.id, 'rating': 5, 'title': 'Actualizada', 'text': 'Texto 2'},
            format='json'
        )
        assert res2.status_code in [200, 201]

        # Debe existir exactamente una review activa para Alice en este libro
        active_reviews = Review.objects.filter(user=alice, book=sample_book, deleted_at__isnull=True)
        assert active_reviews.count() == 1
        assert active_reviews.first().rating == 5

    def test_isbn_normalization_and_deduplication(self, sample_book):
        # Verificar que el ISBN guardado se normalizó sin guiones
        assert sample_book.isbn == '9788437604947'

        author = Author.objects.create(name='Test Author')
        book2 = Book.objects.create(
            title='Libro con ISBN con espacios',
            author=author,
            isbn='  978 84 376 0494 8  '
        )
        assert book2.isbn == '9788437604948'

    def test_invalid_rating_rejected(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        # 1. Review con rating > 10
        res_review_high = api_client.post(
            '/api/v1/books/reviews/',
            {'book_id': sample_book.id, 'rating': 15, 'title': 'Inválido'},
            format='json'
        )
        assert res_review_high.status_code == 400

        # 2. Review con rating < 1
        res_review_low = api_client.post(
            '/api/v1/books/reviews/',
            {'book_id': sample_book.id, 'rating': 0, 'title': 'Inválido'},
            format='json'
        )
        assert res_review_low.status_code == 400

        # 3. UserBook con rating inválido
        res_ub_high = api_client.post(
            '/api/v1/books/user/books/',
            {'book_id': sample_book.id, 'rating': 12, 'status': 'reading'},
            format='json'
        )
        assert res_ub_high.status_code == 400

    def test_invalid_reading_status_rejected(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        res = api_client.post(
            '/api/v1/books/user/books/',
            {'book_id': sample_book.id, 'status': 'estado_inexistente'},
            format='json'
        )
        assert res.status_code == 400

    def test_invalid_reading_progress_rejected(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        # Progreso > 100%
        res_high = api_client.post(
            '/api/v1/books/user/books/',
            {'book_id': sample_book.id, 'progress': 120, 'status': 'reading'},
            format='json'
        )
        assert res_high.status_code == 400

        # Progreso negativo
        res_neg = api_client.post(
            '/api/v1/books/user/books/',
            {'book_id': sample_book.id, 'progress': -10, 'status': 'reading'},
            format='json'
        )
        assert res_neg.status_code == 400


# ============================================================================
# 3. SOCIAL
# ============================================================================
@pytest.mark.django_db
class TestPhase40Social:
    def test_follow_user_flow(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        api_client.force_authenticate(user=alice)

        # Alice sigue a Bob
        res = api_client.post(f'/api/v1/users/{bob.id}/follow/')
        assert res.status_code == 200
        assert alice.following.filter(id=bob.id).exists()

        # Intentar seguirlo de nuevo
        res_duplicate = api_client.post(f'/api/v1/users/{bob.id}/follow/')
        assert res_duplicate.status_code == 400
        assert 'ya sigues' in res_duplicate.data.get('detail', '').lower()

        # Auto-seguimiento rechazado
        res_self = api_client.post(f'/api/v1/users/{alice.id}/follow/')
        assert res_self.status_code == 400

    def test_unfollow_user_flow(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        alice.following.add(bob)
        assert alice.following.filter(id=bob.id).exists()

        api_client.force_authenticate(user=alice)
        res = api_client.post(f'/api/v1/users/{bob.id}/unfollow/')
        assert res.status_code == 200
        assert not alice.following.filter(id=bob.id).exists()

    def test_block_user_flow(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        # Ambos se siguen previamente
        alice.following.add(bob)
        bob.following.add(alice)

        api_client.force_authenticate(user=alice)
        res_block = api_client.post(f'/api/v1/users/{bob.id}/block/')
        assert res_block.status_code == 200
        assert alice.blocked_users.filter(id=bob.id).exists()

        # Ruptura bidireccional inmediata
        assert not alice.following.filter(id=bob.id).exists()
        assert not bob.following.filter(id=alice.id).exists()

        # Auto-bloqueo rechazado
        res_self = api_client.post(f'/api/v1/users/{alice.id}/block/')
        assert res_self.status_code == 400

    def test_unblock_user_flow(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        alice.blocked_users.add(bob)
        assert alice.blocked_users.filter(id=bob.id).exists()

        api_client.force_authenticate(user=alice)
        res_unblock = api_client.post(f'/api/v1/users/{bob.id}/unblock/')
        assert res_unblock.status_code == 200
        assert not alice.blocked_users.filter(id=bob.id).exists()

    def test_follow_blocked_user_prevented(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        # Alice bloquea a Bob
        alice.blocked_users.add(bob)

        # 1. Alice no puede seguir a Bob (está bloqueado)
        api_client.force_authenticate(user=alice)
        res1 = api_client.post(f'/api/v1/users/{bob.id}/follow/')
        assert res1.status_code == 403

        # 2. Bob no puede seguir a Alice (Alice lo tiene bloqueado)
        api_client.force_authenticate(user=bob)
        res2 = api_client.post(f'/api/v1/users/{alice.id}/follow/')
        assert res2.status_code == 403


# ============================================================================
# 4. INTEGRACIÓN
# ============================================================================
@pytest.mark.django_db
class TestPhase40Integration:
    def test_external_book_import_flow(self, api_client, test_users):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        mock_gb_response = MagicMock()
        mock_gb_response.ok = True
        mock_gb_response.status_code = 200
        mock_gb_response.json.return_value = {
            'items': [
                {
                    'id': 'ext12345',
                    'volumeInfo': {
                        'title': 'Crónica de una muerte anunciada',
                        'authors': ['Gabriel García Márquez'],
                        'description': 'Novela basada en un hecho real.',
                        'industryIdentifiers': [{'type': 'ISBN_13', 'identifier': '9788439720775'}],
                        'imageLinks': {'thumbnail': 'https://books.google.com/cronica.jpg'},
                        'categories': ['Novela', 'Ficción'],
                    }
                }
            ]
        }

        with patch('requests.get', return_value=mock_gb_response):
            from books.services import import_multiple_by_title
            books = import_multiple_by_title('Crónica de una muerte anunciada')
            assert len(books) >= 1
            imported_book = books[0]
            assert imported_book.title == 'Crónica de una muerte anunciada'
            assert imported_book.author.name == 'Gabriel García Márquez'
            assert imported_book.isbn == '9788439720775'

    def test_external_providers_resilience(self):
        import requests
        from books.services import GoogleBooksProvider, OpenLibraryProvider

        # Simular timeout en Google Books
        with patch('requests.get', side_effect=requests.exceptions.Timeout('Timeout error')):
            gb_provider = GoogleBooksProvider()
            gb_results = gb_provider.search_by_title('Libro Inexistente')
            assert gb_results == []

        # Simular HTTP 500 en Open Library
        mock_error_resp = MagicMock()
        mock_error_resp.ok = False
        mock_error_resp.status_code = 500
        with patch('requests.get', return_value=mock_error_resp):
            ol_provider = OpenLibraryProvider()
            ol_results = ol_provider.search_by_title('Libro Inexistente')
            assert ol_results == []

    def test_chat_conversation_and_messaging_flow(self, api_client, test_users):
        alice = test_users['alice']
        bob = test_users['bob']

        # Se requiere relación de seguimiento para chatear según la política can_message
        alice.following.add(bob)

        # Alice inicia conversación con Bob
        api_client.force_authenticate(user=alice)
        res_start = api_client.post('/api/v1/conversations/start/', {'user_id': bob.id}, format='json')
        assert res_start.status_code == 200
        conv_id = res_start.data['conversation_id']

        # Alice envía mensaje
        res_msg = api_client.post(
            '/api/v1/messages/',
            {'conversation': conv_id, 'text': '¡Hola Bob!'},
            format='json'
        )
        assert res_msg.status_code == 201
        msg_id = res_msg.data['id']

        # Bob se autentica y lee el mensaje
        api_client.force_authenticate(user=bob)
        res_get_msg = api_client.get(f'/api/v1/messages/{msg_id}/')
        assert res_get_msg.status_code == 200
        assert res_get_msg.data['text'] == '¡Hola Bob!'

    def test_ai_assistant_pipeline(self, api_client, test_users):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        mock_reply = {
            'reply': 'Te recomiendo leer "El coronel no tiene quien le escriba".',
            'model': 'llama3.2',
            'suggested_books': [],
        }

        with patch('books.ai_views.get_assistant_reply', return_value=mock_reply):
            res = api_client.post(
                '/api/v1/books/ai/assistant/',
                {'messages': [{'role': 'user', 'content': 'Recomiéndame algo de realismo mágico.'}]},
                format='json'
            )
            assert res.status_code == 200
            assert 'recomiendo' in res.data['reply'].lower()

    def test_recommendations_endpoint(self, api_client, test_users, sample_book):
        alice = test_users['alice']
        api_client.force_authenticate(user=alice)

        res = api_client.get('/api/v1/books/recommendations/')
        assert res.status_code == 200
        assert 'results' in res.data or isinstance(res.data, list)

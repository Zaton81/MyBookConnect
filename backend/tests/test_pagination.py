from django.contrib.auth import get_user_model
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Review, UserBook
from messages_app.models import Conversation, Message

User = get_user_model()


@pytest.mark.django_db
class TestGlobalPagination:
    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='lector_paginado',
            email='lector_pag@test.com',
            password='Password123!',
        )
        self.client.force_authenticate(user=self.user)

    def test_books_list_pagination_default_page_size(self):
        """Verifica que /api/v1/books/ pagine a 20 resultados por defecto con count y next."""
        author = Author.objects.create(name='Autor Prolífico')
        books = [
            Book(title=f'Libro Tomo {i}', author=author, isbn=f'97800000000{i:02d}')
            for i in range(25)
        ]
        Book.objects.bulk_create(books)

        res = self.client.get('/api/v1/books/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        assert 'count' in data
        assert 'next' in data
        assert 'previous' in data
        assert 'results' in data
        assert data['count'] == 25
        assert len(data['results']) == 20
        assert data['previous'] is None
        assert data['next'] is not None

        # Página 2
        res_p2 = self.client.get('/api/v1/books/?page=2')
        assert res_p2.status_code == status.HTTP_200_OK
        data_p2 = res_p2.json()
        assert len(data_p2['results']) == 5
        assert data_p2['next'] is None
        assert data_p2['previous'] is not None

    def test_books_list_custom_page_size_and_max_page_size(self):
        """Verifica el soporte para query param 'page_size' y el límite max_page_size = 100."""
        author = Author.objects.create(name='Autor Parámetros')
        books = [
            Book(title=f'Volumen {i}', author=author, isbn=f'97810000000{i:02d}')
            for i in range(25)
        ]
        Book.objects.bulk_create(books)

        # page_size=7 personalizado
        res_custom = self.client.get('/api/v1/books/?page_size=7')
        assert res_custom.status_code == status.HTTP_200_OK
        data_custom = res_custom.json()
        assert len(data_custom['results']) == 7

        # page_size=200 superior al max_page_size (100) -> se acota a 100
        res_max = self.client.get('/api/v1/books/?page_size=200')
        assert res_max.status_code == status.HTTP_200_OK
        data_max = res_max.json()
        assert len(data_max['results']) == 25

    def test_reviews_pagination(self):
        """Verifica la paginación estándar de reseñas por libro."""
        author = Author.objects.create(name='Autor Reseñado')
        book = Book.objects.create(title='Obra Magna', author=author)

        for i in range(23):
            reviewer = User.objects.create_user(
                username=f'revisor_{i}',
                email=f'rev_{i}@test.com',
                password='Password123!',
            )
            Review.objects.create(
                user=reviewer,
                book=book,
                rating=5,
                text=f'Crítica literaria número {i}',
            )

        res = self.client.get(f'/api/v1/books/reviews/?book={book.id}')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['count'] == 23
        assert len(data['results']) == 20
        assert data['next'] is not None

        # Segunda página de reseñas
        res_p2 = self.client.get(f'/api/v1/books/reviews/?book={book.id}&page=2')
        assert res_p2.status_code == status.HTTP_200_OK
        data_p2 = res_p2.json()
        assert len(data_p2['results']) == 3

    def test_user_books_pagination(self):
        """Verifica la paginación de la biblioteca de usuario."""
        author = Author.objects.create(name='Autor Biblioteca')
        for i in range(22):
            b = Book.objects.create(title=f'Libro Biblioteca {i}', author=author)
            UserBook.objects.create(user=self.user, book=b, rating=4)

        res = self.client.get('/api/v1/books/user/books/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data['count'] == 22
        assert len(data['results']) == 20
        assert data['next'] is not None

    def test_followers_following_pagination(self):
        """Verifica que las listas de seguidores y seguidos utilicen paginación."""
        target_user = User.objects.create_user(
            username='influencer',
            email='inf@test.com',
            password='Password123!',
        )
        self.client.force_authenticate(user=target_user)

        # Crear 24 seguidores
        for i in range(24):
            fan = User.objects.create_user(
                username=f'fan_{i}',
                email=f'fan_{i}@test.com',
                password='Password123!',
            )
            fan.following.add(target_user)

        # Crear 21 seguidos
        for i in range(21):
            idol = User.objects.create_user(
                username=f'idol_{i}',
                email=f'idol_{i}@test.com',
                password='Password123!',
            )
            target_user.following.add(idol)

        res_followers = self.client.get('/api/v1/users/followers/')
        assert res_followers.status_code == status.HTTP_200_OK
        f_data = res_followers.json()
        assert f_data['count'] == 24
        assert len(f_data['results']) == 20

        res_following = self.client.get('/api/v1/users/following/')
        assert res_following.status_code == status.HTTP_200_OK
        ing_data = res_following.json()
        assert ing_data['count'] == 21
        assert len(ing_data['results']) == 20

    def test_messages_cursor_pagination(self):
        """Verifica que los mensajes de chat utilicen CursorPagination."""
        other = User.objects.create_user(
            username='amigo_chat',
            email='amigo@test.com',
            password='Password123!',
        )
        conv = Conversation.objects.create()
        conv.participants.add(self.user, other)

        # Crear 25 mensajes en orden
        for i in range(25):
            Message.objects.create(
                conversation=conv,
                sender=self.user if i % 2 == 0 else other,
                text=f'Mensaje cronológico {i:02d}',
            )

        # Primera página con cursor pagination
        res1 = self.client.get(f'/api/v1/chat/messages/?conversation={conv.id}')
        assert res1.status_code == status.HTTP_200_OK
        data1 = res1.json()

        assert 'results' in data1
        assert 'next' in data1
        assert 'previous' in data1
        assert len(data1['results']) == 20
        assert data1['next'] is not None
        # Primer mensaje debe ser el más antiguo
        assert data1['results'][0]['text'] == 'Mensaje cronológico 00'

        # Obtener segunda página a través del cursor en next
        next_url = data1['next']
        res2 = self.client.get(next_url)
        assert res2.status_code == status.HTTP_200_OK
        data2 = res2.json()
        assert len(data2['results']) == 5
        assert data2['results'][-1]['text'] == 'Mensaje cronológico 24'

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, Review, UserBook
from books.services.recommendation_service import _calculate_user_affinity, get_book_recommendations, get_user_recommendations
from users.models import Activity, ActivityType, UserPost, UserPostComment, UserPostLike

User = get_user_model()


@pytest.mark.django_db
class TestPhase32MultiAuthorProfileAndWall:
    @pytest.fixture(autouse=True)
    def setup_fixture(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            username='lector_pro',
            email='lector@example.com',
            password='Password123!',
        )
        self.user2 = User.objects.create_user(
            username='amigo_lector',
            email='amigo@example.com',
            password='Password123!',
        )
        self.author1 = Author.objects.create(name='Neil Gaiman')
        self.author2 = Author.objects.create(name='Terry Pratchett')
        self.category = Category.objects.create(name='Fantasía', slug='fantasia')

        # Libro coescrito por ambos autores
        self.collab_book = Book.objects.create(
            title='Good Omens',
            author=self.author1,
            description='Las buenas y acertadas profecías de Agnes Nutter.',
        )
        self.collab_book.authors.add(self.author1, self.author2)
        self.collab_book.categories.add(self.category)

    def test_book_multiple_authors_model_and_methods(self):
        """Verifica que un libro puede tener múltiples autores y el método get_author_names funciona."""
        names = self.collab_book.get_author_names()
        assert 'Neil Gaiman' in names
        assert 'Terry Pratchett' in names
        assert self.collab_book.authors.count() == 2
        assert self.collab_book.author == self.author1  # Autor principal preservado

    def test_book_serializer_multiple_authors(self):
        """Verifica que BookSerializer serializa correctamente los coautores y admite author_ids."""
        self.client.force_authenticate(user=self.user1)

        # 1. Lectura
        res = self.client.get(f'/api/v1/books/{self.collab_book.id}/')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert len(data['authors']) == 2
        author_names = [a['name'] for a in data['authors']]
        assert 'Neil Gaiman' in author_names
        assert 'Terry Pratchett' in author_names

        # 2. Creación vía API con múltiples author_ids
        payload = {
            'title': 'Antología Fantástica',
            'author_ids': [self.author1.id, self.author2.id],
            'description': 'Relatos compartidos.',
        }
        create_res = self.client.post('/api/v1/books/', payload, format='json')
        assert create_res.status_code == status.HTTP_201_CREATED
        created_data = create_res.json()
        assert len(created_data['authors']) == 2
        assert created_data['author']['id'] == self.author1.id

    def test_user_profile_reviews_endpoint_and_filtering(self):
        """Verifica la consulta de todas las reseñas de un usuario en su perfil."""
        # user1 escribe 2 reseñas
        rev1 = Review.objects.create(
            user=self.user1,
            book=self.collab_book,
            rating=5,
            title='Divertidísima novela',
            text='Humor inglés en su máxima expresión.',
        )
        book2 = Book.objects.create(title='Sandman', author=self.author1)
        rev2 = Review.objects.create(
            user=self.user1,
            book=book2,
            rating=5,
            title='Una joya gráfica',
            text='Narrativa visual insuperable.',
        )

        # Consulta mediante /api/v1/reviews/?user=<id>
        res = self.client.get(f'/api/v1/reviews/?user={self.user1.id}')
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        results = data.get('results', data)
        assert len(results) == 2
        # Verificar que la información del libro incluye autores
        review_collab = next(r for r in results if r['book']['id'] == self.collab_book.id)
        assert len(review_collab['book']['authors']) >= 2

        # Consulta mediante /api/v1/users/<id>/reviews/
        res_alias = self.client.get(f'/api/v1/users/{self.user1.id}/reviews/')
        assert res_alias.status_code == status.HTTP_200_OK
        alias_results = res_alias.json().get('results', res_alias.json())
        assert len(alias_results) == 2

    def test_wall_posts_lifecycle_and_interactions(self):
        """Valida el ciclo de vida completo de publicaciones en el muro social (crear, listar, like, comentar, borrar)."""
        self.client.force_authenticate(user=self.user1)

        # 1. Crear publicación en el propio muro con libro vinculado
        post_data = {
            'content': '¡Acabo de empezar Good Omens y es hilarante!',
            'book_id': self.collab_book.id,
        }
        res_create = self.client.post(f'/api/v1/users/{self.user1.id}/posts/', post_data, format='json')
        assert res_create.status_code == status.HTTP_201_CREATED
        post_id = res_create.json()['id']
        assert res_create.json()['content'] == post_data['content']
        assert res_create.json()['book']['title'] == 'Good Omens'
        assert 'Neil Gaiman' in res_create.json()['book']['author']

        # 2. Verificar que se creó la actividad social para el Feed
        act = Activity.objects.filter(user=self.user1, type=ActivityType.POST_CREATED, post_id=post_id).first()
        assert act is not None

        # 3. Listar publicaciones del muro
        res_list = self.client.get(f'/api/v1/users/{self.user1.id}/posts/')
        assert res_list.status_code == status.HTTP_200_OK
        assert len(res_list.json()) >= 1

        # 4. user2 da like a la publicación
        self.client.force_authenticate(user=self.user2)
        res_like = self.client.post(f'/api/v1/users/posts/{post_id}/like/')
        assert res_like.status_code == status.HTTP_200_OK
        assert res_like.json()['liked'] is True
        assert res_like.json()['likes_count'] == 1

        # Segundo toggle quita el like
        res_unlike = self.client.post(f'/api/v1/users/posts/{post_id}/like/')
        assert res_unlike.status_code == status.HTTP_200_OK
        assert res_unlike.json()['liked'] is False
        assert res_unlike.json()['likes_count'] == 0

        # 5. user2 comenta en la publicación
        res_comment = self.client.post(
            f'/api/v1/users/posts/{post_id}/comments/',
            {'text': '¡Totalmente de acuerdo! Crowley y Azirafel son inolvidables.'},
            format='json',
        )
        assert res_comment.status_code == status.HTTP_201_CREATED
        assert 'Crowley' in res_comment.json()['text']

        # Consultar comentarios
        res_get_comments = self.client.get(f'/api/v1/users/posts/{post_id}/comments/')
        assert res_get_comments.status_code == status.HTTP_200_OK
        assert len(res_get_comments.json()) == 1

        # 6. Eliminar publicación (user1 es el autor del post y dueño del muro)
        self.client.force_authenticate(user=self.user1)
        res_del = self.client.delete(f'/api/v1/users/posts/{post_id}/')
        assert res_del.status_code == status.HTTP_204_NO_CONTENT
        assert not UserPost.objects.filter(id=post_id).exists()

    def test_multi_author_recommendation_affinity(self):
        """Verifica que el motor de recomendaciones reconoce la afinidad por coautoría (Fase 32)."""
        # user1 leyó y valoró con 5 estrellas un libro de Terry Pratchett
        pratchett_solo_book = Book.objects.create(
            title='Mundodisco: El color de la magia',
            author=self.author2,
        )
        UserBook.objects.create(user=self.user1, book=pratchett_solo_book, rating=5)

        # _calculate_user_affinity debe incluir afinidad alta para Terry Pratchett
        cat_aff, auth_aff, _ = _calculate_user_affinity(self.user1)
        assert self.author2.id in auth_aff
        assert auth_aff[self.author2.id] > 0.0

        # get_book_recommendations item-to-item: Good Omens debe relacionarse con El color de la magia por coautoría
        similar = get_book_recommendations(book_id=self.collab_book.id, limit=5)
        titles = [item['title'] for item in similar]
        assert 'Mundodisco: El color de la magia' in titles

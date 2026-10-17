import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book, ReadingList, ReadingListFollow, ReadingListItem, ReadingListPrivacy

User = get_user_model()


@pytest.mark.django_db
class TestReadingListsPhase21:
    """Suite de pruebas exhaustiva para la Fase 21: Listas de Lectura."""

    @pytest.fixture
    def alice(self):
        return User.objects.create_user(username='alice', email='alice@example.com', password='password123')

    @pytest.fixture
    def bob(self):
        return User.objects.create_user(username='bob', email='bob@example.com', password='password123')

    @pytest.fixture
    def charlie(self):
        return User.objects.create_user(username='charlie', email='charlie@example.com', password='password123')

    @pytest.fixture
    def books(self):
        b1 = Book.objects.create(title='Cien años de soledad', isbn='9780307474728')
        b2 = Book.objects.create(title='El amor en los tiempos del cólera', isbn='9780307389732')
        b3 = Book.objects.create(title='Crónica de una muerte anunciada', isbn='9781400034956')
        return [b1, b2, b3]

    def test_create_reading_list(self, alice):
        client = APIClient()
        client.force_authenticate(user=alice)

        res = client.post('/api/v1/books/reading-lists/', {
            'name': 'Mis Favoritos 2026',
            'description': 'Los mejores libros leídos este año',
            'privacy': 'public',
        }, format='json')

        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['name'] == 'Mis Favoritos 2026'
        assert res.data['privacy'] == 'public'
        assert res.data['slug'] == 'mis-favoritos-2026'
        assert res.data['user']['username'] == 'alice'

    def test_edit_and_delete_permissions(self, alice, bob):
        r_list = ReadingList.objects.create(
            user=alice,
            name='Lista de Alice',
            privacy=ReadingListPrivacy.PUBLIC,
        )

        client_bob = APIClient()
        client_bob.force_authenticate(user=bob)

        # Bob intenta editar la lista de Alice -> 403
        res_edit = client_bob.patch(f'/api/v1/books/reading-lists/{r_list.id}/', {'name': 'Hackeado'})
        assert res_edit.status_code == status.HTTP_403_FORBIDDEN

        # Bob intenta borrar -> 403
        res_del = client_bob.delete(f'/api/v1/books/reading-lists/{r_list.id}/')
        assert res_del.status_code == status.HTTP_403_FORBIDDEN

        # Alice puede editar y borrar
        client_alice = APIClient()
        client_alice.force_authenticate(user=alice)

        res_alice_edit = client_alice.patch(f'/api/v1/books/reading-lists/{r_list.id}/', {'name': 'Nombre Editado'})
        assert res_alice_edit.status_code == status.HTTP_200_OK
        assert res_alice_edit.data['name'] == 'Nombre Editado'

        res_alice_del = client_alice.delete(f'/api/v1/books/reading-lists/{r_list.id}/')
        assert res_alice_del.status_code == status.HTTP_204_NO_CONTENT
        assert not ReadingList.objects.filter(id=r_list.id).exists()

    def test_privacy_filtering(self, alice, bob, charlie):
        # Alice crea 3 listas: pública, followers y privada
        l_pub = ReadingList.objects.create(user=alice, name='Pública Alice', privacy=ReadingListPrivacy.PUBLIC)
        l_fol = ReadingList.objects.create(user=alice, name='Followers Alice', privacy=ReadingListPrivacy.FOLLOWERS)
        l_priv = ReadingList.objects.create(user=alice, name='Privada Alice', privacy=ReadingListPrivacy.PRIVATE)

        # Bob sigue a Alice
        bob.following.add(alice)

        # Charlie NO sigue a Alice
        client_charlie = APIClient()
        client_charlie.force_authenticate(user=charlie)
        res_charlie = client_charlie.get('/api/v1/books/reading-lists/')
        charlie_names = [item['name'] for item in res_charlie.data['results']]
        assert 'Pública Alice' in charlie_names
        assert 'Followers Alice' not in charlie_names
        assert 'Privada Alice' not in charlie_names

        # Bob consulta listas -> Ve pública y followers (porque la sigue), pero NO privada
        client_bob = APIClient()
        client_bob.force_authenticate(user=bob)
        res_bob = client_bob.get('/api/v1/books/reading-lists/')
        bob_names = [item['name'] for item in res_bob.data['results']]
        assert 'Pública Alice' in bob_names
        assert 'Followers Alice' in bob_names
        assert 'Privada Alice' not in bob_names

        # Alice consulta -> Ve todas sus listas
        client_alice = APIClient()
        client_alice.force_authenticate(user=alice)
        res_alice = client_alice.get('/api/v1/books/reading-lists/?my_lists=true')
        alice_names = [item['name'] for item in res_alice.data['results']]
        assert 'Pública Alice' in alice_names
        assert 'Followers Alice' in alice_names
        assert 'Privada Alice' in alice_names

    def test_add_remove_and_reorder_books(self, alice, books):
        b1, b2, b3 = books
        r_list = ReadingList.objects.create(user=alice, name='Ciencia Ficción', privacy=ReadingListPrivacy.PUBLIC)

        client = APIClient()
        client.force_authenticate(user=alice)

        # Añadir libro 1
        res1 = client.post(f'/api/v1/books/reading-lists/{r_list.id}/add-book/', {'book_id': b1.id, 'notes': 'Imprescindible'})
        assert res1.status_code == status.HTTP_201_CREATED
        assert res1.data['book']['id'] == b1.id
        assert res1.data['position'] == 1

        # Añadir libro 2
        res2 = client.post(f'/api/v1/books/reading-lists/{r_list.id}/add-book/', {'book_id': b2.id})
        assert res2.status_code == status.HTTP_201_CREATED
        assert res2.data['position'] == 2

        # Intentar duplicar libro 1 -> 400
        res_dup = client.post(f'/api/v1/books/reading-lists/{r_list.id}/add-book/', {'book_id': b1.id})
        assert res_dup.status_code == status.HTTP_400_BAD_REQUEST

        # Reordenar (poner b2 en pos 1 y b1 en pos 2)
        res_reorder = client.post(f'/api/v1/books/reading-lists/{r_list.id}/reorder/', {
            'items': [
                {'book_id': b2.id, 'position': 1},
                {'book_id': b1.id, 'position': 2},
            ]
        }, format='json')
        assert res_reorder.status_code == status.HTTP_200_OK
        items = res_reorder.data['items']
        assert items[0]['book']['id'] == b2.id
        assert items[1]['book']['id'] == b1.id

        # Quitar libro 1
        res_rem = client.delete(f'/api/v1/books/reading-lists/{r_list.id}/remove-book/?book_id={b1.id}')
        assert res_rem.status_code == status.HTTP_200_OK
        assert not ReadingListItem.objects.filter(reading_list=r_list, book=b1).exists()
        assert ReadingListItem.objects.filter(reading_list=r_list, book=b2).exists()

    def test_follow_and_unfollow_reading_list(self, alice, bob):
        r_list = ReadingList.objects.create(user=alice, name='Favoritos de Alice', privacy=ReadingListPrivacy.PUBLIC)

        # Alice intenta seguir su propia lista -> 400
        client_alice = APIClient()
        client_alice.force_authenticate(user=alice)
        res_self = client_alice.post(f'/api/v1/books/reading-lists/{r_list.id}/follow/')
        assert res_self.status_code == status.HTTP_400_BAD_REQUEST

        # Bob sigue la lista de Alice
        client_bob = APIClient()
        client_bob.force_authenticate(user=bob)
        res_fol = client_bob.post(f'/api/v1/books/reading-lists/{r_list.id}/follow/')
        assert res_fol.status_code == status.HTTP_200_OK
        assert ReadingListFollow.objects.filter(user=bob, reading_list=r_list).exists()

        # Detalle consultado por Bob indica is_following: True
        res_detail = client_bob.get(f'/api/v1/books/reading-lists/{r_list.id}/')
        assert res_detail.data['is_following'] is True
        assert res_detail.data['followers_count'] == 1

        # Bob deja de seguir la lista
        res_unfol = client_bob.post(f'/api/v1/books/reading-lists/{r_list.id}/unfollow/')
        assert res_unfol.status_code == status.HTTP_200_OK
        assert not ReadingListFollow.objects.filter(user=bob, reading_list=r_list).exists()

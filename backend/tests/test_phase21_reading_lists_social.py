"""
Suite de pruebas automatizadas para la Fase 21 — Listas Sociales.
Verifica:
- Clonar / Duplicar listas de lectura con preservación de libros, posiciones y notas.
- Publicación, listado y eliminación de comentarios en listas de lectura con control de autoría.
- Incremento de apertura/visualización (views_count) al consultar detalles de listas de otros lectores.
- Seguimiento de listas (follow/unfollow) y métricas de items_count, followers_count y comments_count.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Author, Book, Category, ReadingList, ReadingListItem, ReadingListPrivacy

UserModel = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def social_lists_setup(db):
    author = Author.objects.create(name="Ursula K. Le Guin")
    cat = Category.objects.create(name="Ciencia Ficción Humanista", slug="scifi-humanista")

    book1 = Book.objects.create(
        title="Los desposeídos",
        isbn="9788445070284",
        author=author,
        average_rating=4.9,
    )
    book1.categories.add(cat)

    book2 = Book.objects.create(
        title="La mano izquierda de la oscuridad",
        isbn="9788445070291",
        author=author,
        average_rating=4.8,
    )
    book2.categories.add(cat)

    user_creator = UserModel.objects.create_user(
        username="list_creator",
        email="creator@example.com",
        password="Password123!",
    )

    user_reader = UserModel.objects.create_user(
        username="list_reader",
        email="reader@example.com",
        password="Password123!",
    )

    user_other = UserModel.objects.create_user(
        username="other_person",
        email="other@example.com",
        password="Password123!",
    )

    reading_list = ReadingList.objects.create(
        user=user_creator,
        name="Clásicos de Ursula K. Le Guin",
        description="Selección indispensable de ciencia ficción filosófica.",
        privacy=ReadingListPrivacy.PUBLIC,
    )

    ReadingListItem.objects.create(
        reading_list=reading_list,
        book=book1,
        position=1,
        notes="Obra clave sobre el anarquismo y el utopismo.",
    )
    ReadingListItem.objects.create(
        reading_list=reading_list,
        book=book2,
        position=2,
        notes="Exploración profunda sobre el género y la diplomacia.",
    )

    return {
        'creator': user_creator,
        'reader': user_reader,
        'other': user_other,
        'list': reading_list,
        'book1': book1,
        'book2': book2,
    }


@pytest.mark.django_db
class TestPhase21ReadingListsSocial:
    """Pruebas funcionales de las capacidades sociales y de métricas en Listas de Lectura."""

    def test_clone_reading_list_success(self, api_client, social_lists_setup):
        """Un usuario puede clonar una lista ajena a su propia biblioteca."""
        reader = social_lists_setup['reader']
        source_list = social_lists_setup['list']

        api_client.force_authenticate(user=reader)
        response = api_client.post(f"/api/v1/books/reading-lists/{source_list.id}/clone/")
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data['user']['username'] == reader.username
        assert "Copia de" in data['name']
        assert data['privacy'] == ReadingListPrivacy.PRIVATE
        assert data['items_count'] == 2

        # Verificar que los elementos clonados son copias independientes
        cloned_list_id = data['id']
        cloned_items = ReadingListItem.objects.filter(reading_list_id=cloned_list_id).order_by('position')
        assert cloned_items.count() == 2
        assert cloned_items[0].book_id == social_lists_setup['book1'].id
        assert cloned_items[0].notes == "Obra clave sobre el anarquismo y el utopismo."

    def test_list_comments_crud_and_permissions(self, api_client, social_lists_setup):
        """Añadir, listar y eliminar comentarios en una lista de lectura."""
        reader = social_lists_setup['reader']
        other = social_lists_setup['other']
        r_list = social_lists_setup['list']

        # 1. Comentar como reader
        api_client.force_authenticate(user=reader)
        comment_resp = api_client.post(
            f"/api/v1/books/reading-lists/{r_list.id}/comments/",
            {'content': '¡Excelente selección! Me cambió la forma de ver la ciencia ficción.'},
            format='json',
        )
        assert comment_resp.status_code == status.HTTP_201_CREATED
        comment_id = comment_resp.json()['id']
        assert comment_resp.json()['user']['username'] == reader.username

        # 2. Consultar comentarios públicamente
        api_client.force_authenticate(user=None)
        list_resp = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/comments/")
        assert list_resp.status_code == status.HTTP_200_OK
        comments_list = list_resp.json()
        assert len(comments_list) == 1
        assert "Excelente selección" in comments_list[0]['content']

        # 3. Usuario ajeno intenta borrar el comentario -> 403 Forbidden
        api_client.force_authenticate(user=other)
        del_forbidden = api_client.delete(f"/api/v1/books/reading-lists/{r_list.id}/comments/{comment_id}/")
        assert del_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # 4. Autor del comentario lo borra exitosamente -> 200 OK
        api_client.force_authenticate(user=reader)
        del_ok = api_client.delete(f"/api/v1/books/reading-lists/{r_list.id}/comments/{comment_id}/")
        assert del_ok.status_code == status.HTTP_200_OK

        # 5. Ya no aparece en el listado activo
        list_after = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/comments/")
        assert len(list_after.json()) == 0

    def test_views_count_auto_increment(self, api_client, social_lists_setup):
        """Consultar el detalle de una lista por otro lector incrementa views_count."""
        reader = social_lists_setup['reader']
        creator = social_lists_setup['creator']
        r_list = social_lists_setup['list']
        initial_views = r_list.views_count

        # Consulta por otro lector -> Se incrementa
        api_client.force_authenticate(user=reader)
        resp1 = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/")
        assert resp1.status_code == status.HTTP_200_OK
        assert resp1.json()['views_count'] == initial_views + 1

        # Consulta por el creador -> No se auto-incrementa
        api_client.force_authenticate(user=creator)
        resp2 = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/")
        assert resp2.status_code == status.HTTP_200_OK
        assert resp2.json()['views_count'] == initial_views + 1

    def test_follow_unfollow_and_metrics(self, api_client, social_lists_setup):
        """Seguir y dejar de seguir una lista actualiza followers_count e is_following."""
        reader = social_lists_setup['reader']
        r_list = social_lists_setup['list']

        api_client.force_authenticate(user=reader)

        # 1. Detalle inicial: followers_count = 0, is_following = False
        res_init = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/")
        assert res_init.json()['followers_count'] == 0
        assert res_init.json()['is_following'] is False

        # 2. Seguir lista
        follow_res = api_client.post(f"/api/v1/books/reading-lists/{r_list.id}/follow/")
        assert follow_res.status_code == status.HTTP_200_OK

        # 3. Detalle tras follow: followers_count = 1, is_following = True
        res_followed = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/")
        assert res_followed.json()['followers_count'] == 1
        assert res_followed.json()['is_following'] is True

        # 4. Dejar de seguir
        unfollow_res = api_client.post(f"/api/v1/books/reading-lists/{r_list.id}/unfollow/")
        assert unfollow_res.status_code == status.HTTP_200_OK

        # 5. Detalle tras unfollow: followers_count = 0, is_following = False
        res_unfollowed = api_client.get(f"/api/v1/books/reading-lists/{r_list.id}/")
        assert res_unfollowed.json()['followers_count'] == 0
        assert res_unfollowed.json()['is_following'] is False

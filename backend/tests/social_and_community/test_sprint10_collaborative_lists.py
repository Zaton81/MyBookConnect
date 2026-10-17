import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    Book,
    ReadingList,
    ReadingListCollaborator,
    ReadingListItem,
    ReadingListPrivacy,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def list_owner(db):
    return User.objects.create_user(
        username="list_owner",
        email="owner@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def collaborator_user(db):
    return User.objects.create_user(
        username="collaborator_user",
        email="collab@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def outsider_user(db):
    return User.objects.create_user(
        username="outsider_user",
        email="outsider@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def sample_books(db):
    author = Author.objects.create(name="Julio Cortázar")
    b1 = Book.objects.create(title="Rayuela", author=author, isbn="9788437604572")
    b2 = Book.objects.create(title="Bestiario", author=author, isbn="9788420424590")
    b3 = Book.objects.create(title="Final del juego", author=author, isbn="9788466332156")
    return [b1, b2, b3]


@pytest.fixture
def reading_list(list_owner):
    return ReadingList.objects.create(
        user=list_owner,
        name="Lista de Realismo Mágico y Fantástico",
        description="Selección especial",
        privacy=ReadingListPrivacy.PUBLIC,
        is_collaborative=False,
    )


@pytest.mark.django_db
class TestSprint10CollaborativeLists:
    def test_owner_can_invite_collaborator(self, api_client, list_owner, collaborator_user, reading_list):
        api_client.force_authenticate(user=list_owner)
        response = api_client.post(
            f"/api/v1/books/reading-lists/{reading_list.id}/collaborators/",
            {
                "user_id": collaborator_user.id,
                "role": "EDITOR",
                "can_add_books": True,
                "can_remove_books": False,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "PENDING"
        assert response.data["user"]["id"] == collaborator_user.id
        assert response.data["can_add_books"] is True
        assert response.data["can_remove_books"] is False

        reading_list.refresh_from_db()
        assert reading_list.is_collaborative is True
        assert ReadingListCollaborator.objects.filter(
            reading_list=reading_list, user=collaborator_user, status="PENDING"
        ).exists()

    def test_collaborator_can_accept_invitation(self, api_client, list_owner, collaborator_user, reading_list):
        collab = ReadingListCollaborator.objects.create(
            reading_list=reading_list,
            user=collaborator_user,
            invited_by=list_owner,
            role="EDITOR",
            status="PENDING",
            can_add_books=True,
            can_remove_books=False,
        )
        reading_list.is_collaborative = True
        reading_list.save()

        api_client.force_authenticate(user=collaborator_user)
        response = api_client.patch(
            f"/api/v1/books/reading-lists/{reading_list.id}/collaborators/{collaborator_user.id}/",
            {"status": "ACCEPTED"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ACCEPTED"

        collab.refresh_from_db()
        assert collab.status == "ACCEPTED"

    def test_collaborator_can_add_book_and_sets_added_by(
        self, api_client, list_owner, collaborator_user, reading_list, sample_books
    ):
        reading_list.is_collaborative = True
        reading_list.save()
        ReadingListCollaborator.objects.create(
            reading_list=reading_list,
            user=collaborator_user,
            invited_by=list_owner,
            role="EDITOR",
            status="ACCEPTED",
            can_add_books=True,
            can_remove_books=False,
        )

        api_client.force_authenticate(user=collaborator_user)
        response = api_client.post(
            f"/api/v1/books/reading-lists/{reading_list.id}/add-book/",
            {"book_id": sample_books[0].id, "notes": "Aportado por colaborador"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["added_by"]["id"] == collaborator_user.id
        assert response.data["added_by"]["username"] == collaborator_user.username

        item = ReadingListItem.objects.get(reading_list=reading_list, book=sample_books[0])
        assert item.added_by == collaborator_user
        assert item.notes == "Aportado por colaborador"

    def test_collaborator_cannot_remove_others_book_without_permission(
        self, api_client, list_owner, collaborator_user, reading_list, sample_books
    ):
        reading_list.is_collaborative = True
        reading_list.save()
        ReadingListCollaborator.objects.create(
            reading_list=reading_list,
            user=collaborator_user,
            invited_by=list_owner,
            role="EDITOR",
            status="ACCEPTED",
            can_add_books=True,
            can_remove_books=False,
        )

        # Owner added sample_books[1]
        ReadingListItem.objects.create(
            reading_list=reading_list,
            book=sample_books[1],
            position=1,
            added_by=list_owner,
        )

        # Collaborator attempts to remove owner's book
        api_client.force_authenticate(user=collaborator_user)
        response = api_client.delete(
            f"/api/v1/books/reading-lists/{reading_list.id}/remove-book/",
            {"book_id": sample_books[1].id},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert ReadingListItem.objects.filter(reading_list=reading_list, book=sample_books[1]).exists()

    def test_collaborator_can_remove_own_added_book(
        self, api_client, list_owner, collaborator_user, reading_list, sample_books
    ):
        reading_list.is_collaborative = True
        reading_list.save()
        ReadingListCollaborator.objects.create(
            reading_list=reading_list,
            user=collaborator_user,
            invited_by=list_owner,
            role="EDITOR",
            status="ACCEPTED",
            can_add_books=True,
            can_remove_books=False,
        )

        # Collaborator added sample_books[2]
        ReadingListItem.objects.create(
            reading_list=reading_list,
            book=sample_books[2],
            position=1,
            added_by=collaborator_user,
        )

        # Collaborator removes own book
        api_client.force_authenticate(user=collaborator_user)
        response = api_client.delete(
            f"/api/v1/books/reading-lists/{reading_list.id}/remove-book/",
            {"book_id": sample_books[2].id},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert not ReadingListItem.objects.filter(reading_list=reading_list, book=sample_books[2]).exists()

    def test_collaborator_can_leave_list(self, api_client, list_owner, collaborator_user, reading_list):
        reading_list.is_collaborative = True
        reading_list.save()
        collab = ReadingListCollaborator.objects.create(
            reading_list=reading_list,
            user=collaborator_user,
            invited_by=list_owner,
            role="EDITOR",
            status="ACCEPTED",
        )

        api_client.force_authenticate(user=collaborator_user)
        response = api_client.delete(
            f"/api/v1/books/reading-lists/{reading_list.id}/collaborators/{collaborator_user.id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert not ReadingListCollaborator.objects.filter(id=collab.id).exists()

    def test_collaborative_query_param_filters_correctly(
        self, api_client, list_owner, collaborator_user, outsider_user, reading_list
    ):
        reading_list.is_collaborative = True
        reading_list.save()
        ReadingListCollaborator.objects.create(
            reading_list=reading_list,
            user=collaborator_user,
            invited_by=list_owner,
            role="EDITOR",
            status="ACCEPTED",
        )

        # Collaborator sees it with ?collaborative=true
        api_client.force_authenticate(user=collaborator_user)
        res = api_client.get("/api/v1/books/reading-lists/?collaborative=true")
        assert res.status_code == status.HTTP_200_OK
        assert any(item["id"] == reading_list.id for item in res.data["results"])

        # Outsider does NOT see it with ?collaborative=true
        api_client.force_authenticate(user=outsider_user)
        res2 = api_client.get("/api/v1/books/reading-lists/?collaborative=true")
        assert res2.status_code == status.HTTP_200_OK
        assert not any(item["id"] == reading_list.id for item in res2.data["results"])

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    Book,
    ReadingClub,
    ReadingClubMember,
    ReadingClubBook,
    ReadingClubDiscussion,
    ReadingClubDiscussionComment,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def club_creator(db):
    return User.objects.create_user(
        username="club_creator",
        email="creator@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def member_user(db):
    return User.objects.create_user(
        username="club_reader",
        email="reader@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def outsider_user(db):
    return User.objects.create_user(
        username="outsider_reader",
        email="outsider@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def sample_book(db):
    author = Author.objects.create(name="Gabriel García Márquez")
    return Book.objects.create(
        title="Cien años de soledad",
        author=author,
        isbn="9780307474728",
    )


@pytest.mark.django_db
def test_create_public_club_and_auto_admin_membership(api_client, club_creator, sample_book):
    """
    Verifica que al crear un club público, se asigna el rol ADMIN y estado ACTIVE al creador.
    """
    api_client.force_authenticate(user=club_creator)

    payload = {
        "name": "Club de Realismo Mágico",
        "description": "Espacio para debatir obras maestras latinoamericanas.",
        "is_private": False,
        "rules": "Respeto mutuo y debates constructivos.",
    }
    response = api_client.post("/api/v1/clubs/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED
    data = response.data

    assert data["name"] == "Club de Realismo Mágico"
    assert data["slug"] == "club-de-realismo-magico"
    assert data["is_private"] is False

    # Verificar que el creador es ADMIN y ACTIVE
    membership = ReadingClubMember.objects.filter(
        club__slug="club-de-realismo-magico",
        user=club_creator,
    ).first()
    assert membership is not None
    assert membership.role == ReadingClubMember.Role.ADMIN
    assert membership.status == ReadingClubMember.Status.ACTIVE


@pytest.mark.django_db
def test_join_public_club_and_request_private_club(api_client, club_creator, member_user, outsider_user):
    """
    Verifica que en un club público la unión es directa (ACTIVE),
    mientras que en un club privado queda en estado PENDING.
    """
    # 1. Crear club público y unirse directamente
    public_club = ReadingClub.objects.create(
        name="Lectores Clásicos",
        creator=club_creator,
        is_private=False,
    )
    ReadingClubMember.objects.create(
        club=public_club,
        user=club_creator,
        role=ReadingClubMember.Role.ADMIN,
        status=ReadingClubMember.Status.ACTIVE,
    )

    api_client.force_authenticate(user=member_user)
    resp_public = api_client.post(f"/api/v1/clubs/{public_club.slug}/join/")
    assert resp_public.status_code == status.HTTP_201_CREATED
    assert resp_public.data["status"] == ReadingClubMember.Status.ACTIVE

    # 2. Crear club privado y solicitar ingreso
    private_club = ReadingClub.objects.create(
        name="Círculo Secreto Literario",
        creator=club_creator,
        is_private=True,
    )
    ReadingClubMember.objects.create(
        club=private_club,
        user=club_creator,
        role=ReadingClubMember.Role.ADMIN,
        status=ReadingClubMember.Status.ACTIVE,
    )

    api_client.force_authenticate(user=outsider_user)
    resp_private = api_client.post(f"/api/v1/clubs/{private_club.slug}/join/")
    assert resp_private.status_code == status.HTTP_201_CREATED
    assert resp_private.data["status"] == ReadingClubMember.Status.PENDING

    # Verificar que no es visible como miembro activo
    membership = ReadingClubMember.objects.get(club=private_club, user=outsider_user)
    assert membership.status == ReadingClubMember.Status.PENDING


@pytest.mark.django_db
def test_manage_members_and_roles(api_client, club_creator, member_user, outsider_user):
    """
    Verifica que el administrador puede aprobar solicitudes pendientes y promover roles.
    Un miembro normal no puede alterar roles ajenos.
    """
    club = ReadingClub.objects.create(
        name="Club de Novela Negra",
        creator=club_creator,
        is_private=True,
    )
    ReadingClubMember.objects.create(
        club=club,
        user=club_creator,
        role=ReadingClubMember.Role.ADMIN,
        status=ReadingClubMember.Status.ACTIVE,
    )
    pending_member = ReadingClubMember.objects.create(
        club=club,
        user=member_user,
        role=ReadingClubMember.Role.MEMBER,
        status=ReadingClubMember.Status.PENDING,
    )

    # Intento no autorizado por usuario ajeno
    api_client.force_authenticate(user=outsider_user)
    unauthorized_resp = api_client.patch(
        f"/api/v1/clubs/{club.slug}/members/{member_user.id}/",
        {"status": "ACTIVE"},
        format="json",
    )
    assert unauthorized_resp.status_code == status.HTTP_403_FORBIDDEN

    # Administrador aprueba el ingreso
    api_client.force_authenticate(user=club_creator)
    approve_resp = api_client.patch(
        f"/api/v1/clubs/{club.slug}/members/{member_user.id}/",
        {"status": "ACTIVE", "role": "MODERATOR"},
        format="json",
    )
    assert approve_resp.status_code == status.HTTP_200_OK
    assert approve_resp.data["status"] == ReadingClubMember.Status.ACTIVE
    assert approve_resp.data["role"] == ReadingClubMember.Role.MODERATOR


@pytest.mark.django_db
def test_club_reading_plan_and_current_book(api_client, club_creator, member_user, sample_book):
    """
    Verifica que se pueden agendar lecturas en el plan y que asignar status=CURRENT
    actualiza el libro activo del club.
    """
    club = ReadingClub.objects.create(
        name="Club Ficción Histórica",
        creator=club_creator,
    )
    ReadingClubMember.objects.create(
        club=club,
        user=club_creator,
        role=ReadingClubMember.Role.ADMIN,
        status=ReadingClubMember.Status.ACTIVE,
    )

    api_client.force_authenticate(user=club_creator)
    payload = {
        "book_id": sample_book.id,
        "status": "CURRENT",
        "target_milestones": "Capítulos 1 al 5 para el 15 de octubre",
    }
    response = api_client.post(f"/api/v1/clubs/{club.slug}/books/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED

    club.refresh_from_db()
    assert club.current_book == sample_book


@pytest.mark.django_db
def test_club_discussions_and_comments_with_spoilers(api_client, club_creator, member_user, outsider_user, sample_book):
    """
    Verifica creación de debates con avisos de spoilers, comentarios y restricción en clubs privados.
    """
    club = ReadingClub.objects.create(
        name="Club Privado de Misterio",
        creator=club_creator,
        is_private=True,
    )
    ReadingClubMember.objects.create(
        club=club,
        user=club_creator,
        role=ReadingClubMember.Role.ADMIN,
        status=ReadingClubMember.Status.ACTIVE,
    )
    ReadingClubMember.objects.create(
        club=club,
        user=member_user,
        role=ReadingClubMember.Role.MEMBER,
        status=ReadingClubMember.Status.ACTIVE,
    )

    # Miembro crea debate
    api_client.force_authenticate(user=member_user)
    disc_payload = {
        "title": "Debate sobre el final del libro",
        "content": "¿Quién sospechaba del desenlace del capítulo 20?",
        "book_id": sample_book.id,
        "has_spoilers": True,
    }
    disc_resp = api_client.post(f"/api/v1/clubs/{club.slug}/discussions/", disc_payload, format="json")
    assert disc_resp.status_code == status.HTTP_201_CREATED
    discussion_id = disc_resp.data["id"]
    assert disc_resp.data["has_spoilers"] is True

    # Comentario del creador en el debate
    api_client.force_authenticate(user=club_creator)
    comment_payload = {
        "content": "A mí me sorprendió por completo, no lo vi venir.",
        "has_spoilers": True,
    }
    comm_resp = api_client.post(
        f"/api/v1/clubs/{club.slug}/discussions/{discussion_id}/comments/",
        comment_payload,
        format="json",
    )
    assert comm_resp.status_code == status.HTTP_201_CREATED

    # Usuario outsider no perteneciente al club privado no puede listar discusiones
    api_client.force_authenticate(user=outsider_user)
    outsider_list = api_client.get(f"/api/v1/clubs/{club.slug}/discussions/")
    results = outsider_list.data.get('results') if isinstance(outsider_list.data, dict) else outsider_list.data
    assert len(results) == 0


@pytest.mark.django_db
def test_leave_club_validation(api_client, club_creator, member_user):
    """
    Verifica que un miembro puede abandonar el club,
    pero el único administrador no puede abandonarlo sin transferir el rol.
    """
    club = ReadingClub.objects.create(
        name="Club de Poesía",
        creator=club_creator,
    )
    ReadingClubMember.objects.create(
        club=club,
        user=club_creator,
        role=ReadingClubMember.Role.ADMIN,
        status=ReadingClubMember.Status.ACTIVE,
    )
    ReadingClubMember.objects.create(
        club=club,
        user=member_user,
        role=ReadingClubMember.Role.MEMBER,
        status=ReadingClubMember.Status.ACTIVE,
    )

    # Miembro normal sale
    api_client.force_authenticate(user=member_user)
    leave_resp = api_client.post(f"/api/v1/clubs/{club.slug}/leave/")
    assert leave_resp.status_code == status.HTTP_200_OK
    assert not ReadingClubMember.objects.filter(club=club, user=member_user).exists()

    # Único admin intenta salir
    api_client.force_authenticate(user=club_creator)
    admin_leave_resp = api_client.post(f"/api/v1/clubs/{club.slug}/leave/")
    assert admin_leave_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "único administrador" in admin_leave_resp.data["detail"]

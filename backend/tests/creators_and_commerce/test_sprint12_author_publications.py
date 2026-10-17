import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    AuthorAnnouncement,
    AuthorProfile,
    Book,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def author_user(db):
    return User.objects.create_user(
        username="author_garcia_marquez",
        email="gabo@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def reader_user(db):
    return User.objects.create_user(
        username="reader_fernando",
        email="fernando@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def author_entity(db, author_user):
    author = Author.objects.create(
        name="Gabriel García Márquez",
        claimed_by=author_user,
        is_verified=True,
    )
    AuthorProfile.objects.create(
        user=author_user,
        author=author,
        pen_name="Gabo",
        is_verified=True,
    )
    return author


@pytest.fixture
def sample_book(db, author_entity):
    return Book.objects.create(
        title="Cien años de soledad",
        author=author_entity,
        isbn="9788420471839",
    )


@pytest.mark.django_db
def test_verified_author_can_create_advanced_publication(api_client, author_user, author_entity, sample_book):
    api_client.force_authenticate(user=author_user)
    long_content = "Muchos años después, frente al pelotón de fusilamiento, el coronel Aureliano Buendía había de recordar aquella tarde remota en que su padre lo llevó a conocer el hielo. " * 15

    payload = {
        "author": author_entity.id,
        "book": sample_book.id,
        "title": "Adelanto exclusivo del capítulo inédito",
        "content": long_content,
        "publication_type": "CHAPTER_PREVIEW",
        "has_spoilers": True,
        "spoiler_warning": "Contiene detalles cruciales sobre Macondo.",
        "is_pinned": True,
    }

    response = api_client.post("/api/v1/books/author-publications/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["title"] == payload["title"]
    assert response.data["publication_type"] == "CHAPTER_PREVIEW"
    assert response.data["has_spoilers"] is True
    assert response.data["is_pinned"] is True
    assert response.data["excerpt"] != ""
    assert response.data["estimated_reading_time"] >= 1

    post = AuthorAnnouncement.objects.get(id=response.data["id"])
    assert post.author == author_entity
    assert post.book == sample_book


@pytest.mark.django_db
def test_unauthorized_user_cannot_publish_for_another_author(api_client, reader_user, author_entity):
    api_client.force_authenticate(user=reader_user)

    payload = {
        "author": author_entity.id,
        "title": "Publicación no autorizada",
        "content": "Intento de usurpación.",
        "publication_type": "ANNOUNCEMENT",
    }

    response = api_client.post("/api/v1/books/author-publications/", payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_author_can_save_and_retrieve_drafts(api_client, author_user, reader_user, author_entity):
    api_client.force_authenticate(user=author_user)

    draft_payload = {
        "author": author_entity.id,
        "title": "Borrador de notas de autor",
        "content": "Ideas tempranas para la nueva novela.",
        "publication_type": "AUTHOR_DIARY",
        "is_draft": True,
    }
    create_res = api_client.post("/api/v1/books/author-publications/", draft_payload, format="json")
    assert create_res.status_code == status.HTTP_201_CREATED
    assert create_res.data["is_draft"] is True

    # Public list (anónimo o lector) does not show draft
    api_client.force_authenticate(user=reader_user)
    pub_res = api_client.get(f"/api/v1/books/author-publications/?author={author_entity.id}")
    assert pub_res.status_code == status.HTTP_200_OK
    pub_items = pub_res.data.get("results", pub_res.data) if isinstance(pub_res.data, dict) else pub_res.data
    assert len(pub_items) == 0

    # Author querying with drafts=true sees their draft
    api_client.force_authenticate(user=author_user)
    author_res = api_client.get(f"/api/v1/books/author-publications/?author={author_entity.id}&drafts=true")
    assert author_res.status_code == status.HTTP_200_OK
    author_items = author_res.data.get("results", author_res.data) if isinstance(author_res.data, dict) else author_res.data
    assert len(author_items) == 1
    assert author_items[0]["is_draft"] is True


@pytest.mark.django_db
def test_filter_publications_by_type_and_book(api_client, author_user, author_entity, sample_book):
    profile = author_user.author_profile

    AuthorAnnouncement.objects.create(
        author_profile=profile,
        author=author_entity,
        book=sample_book,
        title="Diario de Escritura #1",
        content="Notas sobre el proceso de creación.",
        publication_type="AUTHOR_DIARY",
    )
    AuthorAnnouncement.objects.create(
        author_profile=profile,
        author=author_entity,
        book=sample_book,
        title="Escena eliminada: El galeón en la selva",
        content="Fragmento no incluido en la edición final.",
        publication_type="DELETED_SCENE",
    )

    # Filter by publication_type
    res_diary = api_client.get(f"/api/v1/books/author-publications/?author={author_entity.id}&type=AUTHOR_DIARY")
    assert res_diary.status_code == status.HTTP_200_OK
    diary_items = res_diary.data.get("results", res_diary.data) if isinstance(res_diary.data, dict) else res_diary.data
    assert len(diary_items) == 1
    assert diary_items[0]["title"] == "Diario de Escritura #1"

    res_deleted = api_client.get(f"/api/v1/books/author-publications/?author={author_entity.id}&type=DELETED_SCENE")
    assert res_deleted.status_code == status.HTTP_200_OK
    deleted_items = res_deleted.data.get("results", res_deleted.data) if isinstance(res_deleted.data, dict) else res_deleted.data
    assert len(deleted_items) == 1
    assert deleted_items[0]["title"] == "Escena eliminada: El galeón en la selva"


@pytest.mark.django_db
def test_author_can_toggle_pin(api_client, author_user, author_entity):
    profile = author_user.author_profile
    post = AuthorAnnouncement.objects.create(
        author_profile=profile,
        author=author_entity,
        title="Noticia fija",
        content="Contenido relevante.",
        is_pinned=False,
    )

    api_client.force_authenticate(user=author_user)
    res = api_client.post(f"/api/v1/books/author-publications/{post.id}/toggle_pin/")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["is_pinned"] is True

    post.refresh_from_db()
    assert post.is_pinned is True

    # Toggle off
    res2 = api_client.post(f"/api/v1/books/author-publications/{post.id}/toggle_pin/")
    assert res2.status_code == status.HTTP_200_OK
    assert res2.data["is_pinned"] is False


@pytest.mark.django_db
def test_author_can_update_and_delete_own_publication(api_client, author_user, author_entity):
    profile = author_user.author_profile
    post = AuthorAnnouncement.objects.create(
        author_profile=profile,
        author=author_entity,
        title="Título original",
        content="Contenido original.",
    )

    api_client.force_authenticate(user=author_user)
    update_res = api_client.patch(
        f"/api/v1/books/author-publications/{post.id}/",
        {"title": "Título actualizado"},
        format="json",
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.data["title"] == "Título actualizado"

    delete_res = api_client.delete(f"/api/v1/books/author-publications/{post.id}/")
    assert delete_res.status_code == status.HTTP_204_NO_CONTENT
    assert not AuthorAnnouncement.objects.filter(id=post.id).exists()


@pytest.mark.django_db
def test_legacy_announcement_endpoints_continue_working(api_client, author_user, author_entity):
    api_client.force_authenticate(user=author_user)
    legacy_payload = {
        "title": "Comunicado tradicional",
        "content": "Texto del comunicado oficial para lectores.",
    }
    create_res = api_client.post("/api/v1/books/authors/announcements/", legacy_payload, format="json")
    assert create_res.status_code == status.HTTP_201_CREATED
    assert create_res.data["title"] == "Comunicado tradicional"

    list_res = api_client.get(f"/api/v1/books/authors/{author_entity.id}/announcements/")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.data) >= 1

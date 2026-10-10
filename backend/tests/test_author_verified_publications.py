import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    AuthorAnnouncement,
    AuthorProfile,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def verified_author_user(db):
    return User.objects.create_user(
        username="author_verificado",
        email="autor_verificado@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def unverified_author_user(db):
    return User.objects.create_user(
        username="author_no_verificado",
        email="autor_no_verificado@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def reader_user(db):
    return User.objects.create_user(
        username="lector_comun",
        email="lector@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin_supremo",
        email="admin@example.com",
        password="ValidPassword123!",
        role="ADMIN",
    )


@pytest.fixture
def verified_author_entity(db, verified_author_user):
    author = Author.objects.create(
        name="Laura Gallego",
        claimed_by=verified_author_user,
        is_verified=True,
    )
    AuthorProfile.objects.create(
        user=verified_author_user,
        author=author,
        pen_name="Laura Gallego",
        is_verified=True,
    )
    return author


@pytest.fixture
def unverified_author_entity(db, unverified_author_user):
    author = Author.objects.create(
        name="Autor Pendiente",
        claimed_by=unverified_author_user,
        is_verified=False,
    )
    AuthorProfile.objects.create(
        user=unverified_author_user,
        author=author,
        pen_name="Pendiente",
        is_verified=False,
    )
    return author


@pytest.mark.django_db
def test_unverified_claimed_author_cannot_create_publication(api_client, unverified_author_user, unverified_author_entity):
    api_client.force_authenticate(user=unverified_author_user)
    payload = {
        "author": unverified_author_entity.id,
        "title": "Publicación sin verificar",
        "content": "Este texto no debería poder publicarse porque el autor aún no está verificado.",
        "publication_type": "ANNOUNCEMENT",
    }
    response = api_client.post("/api/v1/books/author-publications/", payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_unclaimed_or_other_user_cannot_create_publication(api_client, reader_user, verified_author_entity):
    api_client.force_authenticate(user=reader_user)
    payload = {
        "author": verified_author_entity.id,
        "title": "Suplantación no permitida",
        "content": "Un lector intenta publicar en la página de un autor verificado.",
        "publication_type": "ANNOUNCEMENT",
    }
    response = api_client.post("/api/v1/books/author-publications/", payload, format="json")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_verified_author_can_create_paid_publication(api_client, verified_author_user, verified_author_entity):
    api_client.force_authenticate(user=verified_author_user)
    payload = {
        "author": verified_author_entity.id,
        "title": "Capítulo exclusivo de pago",
        "content": "Adelanto reservado para lectores que apoyen el proyecto.",
        "publication_type": "CHAPTER_PREVIEW",
        "is_paid": True,
        "price": "3.50",
    }
    response = api_client.post("/api/v1/books/author-publications/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["is_paid"] is True
    assert Decimal(str(response.data["price"])) == Decimal("3.50")

    pub = AuthorAnnouncement.objects.get(id=response.data["id"])
    assert pub.is_paid is True
    assert pub.price == Decimal("3.50")
    assert pub.is_moderated is False


@pytest.mark.django_db
def test_author_can_update_and_delete_own_publication(api_client, verified_author_user, verified_author_entity):
    pub = AuthorAnnouncement.objects.create(
        author=verified_author_entity,
        author_profile=AuthorProfile.objects.get(author=verified_author_entity),
        title="Título original",
        content="Contenido original",
        publication_type="ANNOUNCEMENT",
    )
    api_client.force_authenticate(user=verified_author_user)

    # Actualizar
    update_res = api_client.patch(
        f"/api/v1/books/author-publications/{pub.id}/",
        {"title": "Título actualizado por el autor"},
        format="json",
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.data["title"] == "Título actualizado por el autor"

    # Eliminar
    delete_res = api_client.delete(f"/api/v1/books/author-publications/{pub.id}/")
    assert delete_res.status_code == status.HTTP_204_NO_CONTENT
    assert not AuthorAnnouncement.objects.filter(id=pub.id).exists()


@pytest.mark.django_db
def test_unauthorized_user_cannot_update_or_delete_publication(api_client, reader_user, verified_author_entity):
    pub = AuthorAnnouncement.objects.create(
        author=verified_author_entity,
        author_profile=AuthorProfile.objects.get(author=verified_author_entity),
        title="Comunicado oficial",
        content="Contenido protegido",
        publication_type="ANNOUNCEMENT",
    )
    api_client.force_authenticate(user=reader_user)

    update_res = api_client.patch(
        f"/api/v1/books/author-publications/{pub.id}/",
        {"title": "Intento de hackeo"},
        format="json",
    )
    assert update_res.status_code == status.HTTP_403_FORBIDDEN

    delete_res = api_client.delete(f"/api/v1/books/author-publications/{pub.id}/")
    assert delete_res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_admin_can_update_and_delete_any_publication(api_client, admin_user, verified_author_entity):
    pub = AuthorAnnouncement.objects.create(
        author=verified_author_entity,
        author_profile=AuthorProfile.objects.get(author=verified_author_entity),
        title="Comunicado original",
        content="Contenido revisable",
        publication_type="ANNOUNCEMENT",
    )
    api_client.force_authenticate(user=admin_user)

    # Administrador modifica
    update_res = api_client.patch(
        f"/api/v1/books/author-publications/{pub.id}/",
        {"title": "Título corregido por el Administrador"},
        format="json",
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.data["title"] == "Título corregido por el Administrador"

    # Administrador elimina
    delete_res = api_client.delete(f"/api/v1/books/author-publications/{pub.id}/")
    assert delete_res.status_code == status.HTTP_204_NO_CONTENT
    assert not AuthorAnnouncement.objects.filter(id=pub.id).exists()


@pytest.mark.django_db
def test_admin_can_censor_and_restore_publication(api_client, admin_user, verified_author_user, reader_user, verified_author_entity):
    pub = AuthorAnnouncement.objects.create(
        author=verified_author_entity,
        author_profile=AuthorProfile.objects.get(author=verified_author_entity),
        title="Publicación polémica",
        content="Texto controvertido",
        publication_type="ANNOUNCEMENT",
    )

    # 1. Admin censura la publicación
    api_client.force_authenticate(user=admin_user)
    censor_res = api_client.post(
        f"/api/v1/books/author-publications/{pub.id}/censor/",
        {"is_moderated": True, "reason": "Incumple las normas de la comunidad sobre spoilers."},
        format="json",
    )
    assert censor_res.status_code == status.HTTP_200_OK
    assert censor_res.data["is_moderated"] is True
    assert censor_res.data["moderation_reason"] == "Incumple las normas de la comunidad sobre spoilers."

    # 2. Lector anónimo o común NO ve la publicación censurada en el listado
    api_client.force_authenticate(user=reader_user)
    reader_list_res = api_client.get(f"/api/v1/books/author-publications/?author={verified_author_entity.id}")
    assert reader_list_res.status_code == status.HTTP_200_OK
    reader_items = reader_list_res.data if isinstance(reader_list_res.data, list) else reader_list_res.data.get("results", [])
    assert not any(item["id"] == pub.id for item in reader_items)

    # 3. El autor original SÍ puede ver su publicación censurada para conocer el estado
    api_client.force_authenticate(user=verified_author_user)
    author_list_res = api_client.get(f"/api/v1/books/author-publications/?author={verified_author_entity.id}")
    assert author_list_res.status_code == status.HTTP_200_OK
    author_items = author_list_res.data if isinstance(author_list_res.data, list) else author_list_res.data.get("results", [])
    assert any(item["id"] == pub.id for item in author_items)

    # 4. El Administrador SÍ puede verla
    api_client.force_authenticate(user=admin_user)
    admin_list_res = api_client.get(f"/api/v1/books/author-publications/?author={verified_author_entity.id}")
    admin_items = admin_list_res.data if isinstance(admin_list_res.data, list) else admin_list_res.data.get("results", [])
    assert any(item["id"] == pub.id for item in admin_items)

    # 5. Admin restaura la publicación
    restore_res = api_client.post(
        f"/api/v1/books/author-publications/{pub.id}/censor/",
        {"is_moderated": False},
        format="json",
    )
    assert restore_res.status_code == status.HTTP_200_OK
    assert restore_res.data["is_moderated"] is False

    # 6. El lector común vuelve a verla
    api_client.force_authenticate(user=reader_user)
    reader_list_res2 = api_client.get(f"/api/v1/books/author-publications/?author={verified_author_entity.id}")
    reader_items2 = reader_list_res2.data if isinstance(reader_list_res2.data, list) else reader_list_res2.data.get("results", [])
    assert any(item["id"] == pub.id for item in reader_items2)


@pytest.mark.django_db
def test_non_admin_cannot_censor_publication(api_client, verified_author_user, reader_user, verified_author_entity):
    pub = AuthorAnnouncement.objects.create(
        author=verified_author_entity,
        author_profile=AuthorProfile.objects.get(author=verified_author_entity),
        title="Publicación",
        content="Texto",
        publication_type="ANNOUNCEMENT",
    )

    # El autor intenta censurarse a sí mismo por este endpoint
    api_client.force_authenticate(user=verified_author_user)
    res1 = api_client.post(f"/api/v1/books/author-publications/{pub.id}/censor/", {"is_moderated": True})
    assert res1.status_code == status.HTTP_403_FORBIDDEN

    # Un lector intenta censurar
    api_client.force_authenticate(user=reader_user)
    res2 = api_client.post(f"/api/v1/books/author-publications/{pub.id}/censor/", {"is_moderated": True})
    assert res2.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_universal_moderation_admin_hide_and_restore(api_client, admin_user, verified_author_entity):
    pub = AuthorAnnouncement.objects.create(
        author=verified_author_entity,
        author_profile=AuthorProfile.objects.get(author=verified_author_entity),
        title="Publicación para consola universal",
        content="Texto",
        publication_type="ANNOUNCEMENT",
    )

    api_client.force_authenticate(user=admin_user)

    # Consola universal: hide
    hide_res = api_client.post(
        "/api/v1/admin/moderation/hide/",
        {"target_type": "author_publication", "target_id": pub.id, "reason": "Reporte de infracción."},
        format="json",
    )
    assert hide_res.status_code == status.HTTP_200_OK
    pub.refresh_from_db()
    assert pub.is_moderated is True
    assert pub.moderation_reason == "Reporte de infracción."

    # Consola universal: restore
    restore_res = api_client.post(
        "/api/v1/admin/moderation/restore/",
        {"target_type": "author_publication", "target_id": pub.id},
        format="json",
    )
    assert restore_res.status_code == status.HTTP_200_OK
    pub.refresh_from_db()
    assert pub.is_moderated is False

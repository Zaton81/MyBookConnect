import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    AuthorNewsletter,
    AuthorNewsletterIssue,
    AuthorNewsletterSubscriber,
    AuthorProfile,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def author_user(db):
    return User.objects.create_user(
        username="author_allende",
        email="isabel@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def reader_user(db):
    return User.objects.create_user(
        username="reader_carmen",
        email="carmen@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def another_reader(db):
    return User.objects.create_user(
        username="reader_pablo",
        email="pablo@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def author_entity(db, author_user):
    author = Author.objects.create(
        name="Isabel Allende",
        claimed_by=author_user,
        is_verified=True,
    )
    AuthorProfile.objects.create(
        user=author_user,
        author=author,
        pen_name="Isabel Allende",
        is_verified=True,
    )
    return author


@pytest.mark.django_db
def test_author_can_create_and_manage_newsletter(api_client, author_user, author_entity):
    api_client.force_authenticate(user=author_user)

    payload = {
        "author": author_entity.id,
        "title": "Cartas desde mi escritorio",
        "description": "Boletín mensual con reflexiones literarias, lecturas recomendadas y noticias exclusivas.",
        "frequency": "MONTHLY",
        "is_active": True,
    }

    response = api_client.post("/api/v1/books/author-newsletters/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["title"] == payload["title"]
    assert response.data["frequency"] == "MONTHLY"
    assert response.data["active_subscribers_count"] == 0
    assert response.data["sent_issues_count"] == 0

    newsletter = AuthorNewsletter.objects.get(id=response.data["id"])
    assert newsletter.author == author_entity
    assert newsletter.is_active is True


@pytest.mark.django_db
def test_reader_can_subscribe_and_unsubscribe_with_one_click(api_client, reader_user, author_entity):
    newsletter = AuthorNewsletter.objects.create(
        author=author_entity,
        title="Novedades Literarias de Isabel Allende",
        description="Boletín mensual oficial",
        frequency="MONTHLY",
    )

    api_client.force_authenticate(user=reader_user)

    # 1. Suscribirse
    sub_res = api_client.post(f"/api/v1/books/author-newsletters/{newsletter.id}/subscribe/", format="json")
    assert sub_res.status_code == status.HTTP_200_OK, sub_res.data
    assert sub_res.data["is_subscribed"] is True
    assert sub_res.data["active_subscribers_count"] == 1

    subscriber_entry = AuthorNewsletterSubscriber.objects.get(newsletter=newsletter, user=reader_user)
    assert subscriber_entry.is_active is True
    assert subscriber_entry.unsubscribed_at is None

    # 2. Desuscribirse
    unsub_res = api_client.post(f"/api/v1/books/author-newsletters/{newsletter.id}/unsubscribe/", format="json")
    assert unsub_res.status_code == status.HTTP_200_OK, unsub_res.data
    assert unsub_res.data["is_subscribed"] is False
    assert unsub_res.data["active_subscribers_count"] == 0

    subscriber_entry.refresh_from_db()
    assert subscriber_entry.is_active is False
    assert subscriber_entry.unsubscribed_at is not None

    # 3. Re-suscribirse (no crea duplicados, reactiva la fila existente)
    resub_res = api_client.post(f"/api/v1/books/author-newsletters/{newsletter.id}/subscribe/", format="json")
    assert resub_res.status_code == status.HTTP_200_OK, resub_res.data
    assert resub_res.data["is_subscribed"] is True
    assert resub_res.data["active_subscribers_count"] == 1
    assert AuthorNewsletterSubscriber.objects.filter(newsletter=newsletter, user=reader_user).count() == 1


@pytest.mark.django_db
def test_my_subscriptions_endpoint(api_client, reader_user, author_entity):
    newsletter = AuthorNewsletter.objects.create(
        author=author_entity,
        title="Boletín Mensual",
        description="Noticias",
    )
    AuthorNewsletterSubscriber.objects.create(
        newsletter=newsletter,
        user=reader_user,
        is_active=True,
    )

    api_client.force_authenticate(user=reader_user)
    response = api_client.get("/api/v1/books/author-newsletters/my_subscriptions/")
    assert response.status_code == status.HTTP_200_OK, response.data
    assert len(response.data) == 1
    assert response.data[0]["id"] == newsletter.id
    assert response.data[0]["is_subscribed"] is True


@pytest.mark.django_db
def test_author_can_view_subscribers_list_and_stranger_cannot(api_client, author_user, reader_user, another_reader, author_entity):
    newsletter = AuthorNewsletter.objects.create(
        author=author_entity,
        title="Boletín de Prueba",
    )
    AuthorNewsletterSubscriber.objects.create(newsletter=newsletter, user=reader_user, is_active=True)
    AuthorNewsletterSubscriber.objects.create(newsletter=newsletter, user=another_reader, is_active=True)

    # El autor puede ver la lista de suscriptores
    api_client.force_authenticate(user=author_user)
    res_author = api_client.get(f"/api/v1/books/author-newsletters/{newsletter.id}/subscribers/")
    assert res_author.status_code == status.HTTP_200_OK, res_author.data
    results = res_author.data.get("results", res_author.data)
    assert len(results) == 2
    usernames = {item["username"] for item in results}
    assert "reader_carmen" in usernames
    assert "reader_pablo" in usernames

    # Un lector ajeno recibe 403 Forbidden
    api_client.force_authenticate(user=reader_user)
    res_stranger = api_client.get(f"/api/v1/books/author-newsletters/{newsletter.id}/subscribers/")
    assert res_stranger.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_author_can_create_draft_and_send_issue_to_subscribers(api_client, author_user, reader_user, author_entity):
    newsletter = AuthorNewsletter.objects.create(
        author=author_entity,
        title="Boletín de Primavera",
    )
    AuthorNewsletterSubscriber.objects.create(newsletter=newsletter, user=reader_user, is_active=True)

    api_client.force_authenticate(user=author_user)

    # 1. Crear borrador de issue
    issue_payload = {
        "newsletter": newsletter.id,
        "title": "Entrega #1: Primeras páginas de mi nueva novela",
        "subject": "¡Noticia exclusiva para mis lectores!",
        "content": "Queridos amigos lectores, les comparto en primicia las primeras páginas...",
        "status": "DRAFT",
    }
    create_res = api_client.post("/api/v1/books/author-newsletter-issues/", issue_payload, format="json")
    assert create_res.status_code == status.HTTP_201_CREATED, create_res.data
    issue_id = create_res.data["id"]
    assert create_res.data["status"] == "DRAFT"
    assert create_res.data["recipients_count"] == 0

    # 2. Enviar el número a los suscriptores
    send_res = api_client.post(f"/api/v1/books/author-newsletter-issues/{issue_id}/send_issue/", format="json")
    assert send_res.status_code == status.HTTP_200_OK, send_res.data
    assert send_res.data["status"] == "SENT"
    assert send_res.data["recipients_count"] == 1
    assert send_res.data["sent_at"] is not None

    # Verificar en base de datos
    issue = AuthorNewsletterIssue.objects.get(id=issue_id)
    assert issue.status == "SENT"
    assert issue.recipients_count == 1
    assert issue.sent_at is not None


@pytest.mark.django_db
def test_readers_only_see_sent_issues_and_author_sees_all(api_client, author_user, reader_user, author_entity):
    newsletter = AuthorNewsletter.objects.create(
        author=author_entity,
        title="Boletín de Invierno",
    )
    # Crear un issue enviado y un borrador
    AuthorNewsletterIssue.objects.create(
        newsletter=newsletter,
        title="Entrega Pública",
        subject="Asunto 1",
        content="Contenido público",
        status="SENT",
    )
    AuthorNewsletterIssue.objects.create(
        newsletter=newsletter,
        title="Borrador Secreto",
        subject="Asunto 2",
        content="Contenido secreto",
        status="DRAFT",
    )

    # Lector solo ve el enviado
    api_client.force_authenticate(user=reader_user)
    reader_res = api_client.get(f"/api/v1/books/author-newsletter-issues/?newsletter={newsletter.id}")
    assert reader_res.status_code == status.HTTP_200_OK
    reader_results = reader_res.data.get("results", reader_res.data)
    assert len(reader_results) == 1
    assert reader_results[0]["title"] == "Entrega Pública"

    # Autor ve ambos
    api_client.force_authenticate(user=author_user)
    author_res = api_client.get(f"/api/v1/books/author-newsletter-issues/?newsletter={newsletter.id}")
    assert author_res.status_code == status.HTTP_200_OK
    author_results = author_res.data.get("results", author_res.data)
    assert len(author_results) == 2


@pytest.mark.django_db
def test_unauthorized_user_cannot_create_or_send_issues(api_client, reader_user, author_entity):
    newsletter = AuthorNewsletter.objects.create(
        author=author_entity,
        title="Boletín Privado",
    )

    api_client.force_authenticate(user=reader_user)
    payload = {
        "newsletter": newsletter.id,
        "title": "Intento ilegítimo",
        "subject": "Spam",
        "content": "Texto no autorizado",
    }
    response = api_client.post("/api/v1/books/author-newsletter-issues/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "newsletter" in response.data

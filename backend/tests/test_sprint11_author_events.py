import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Author,
    AuthorEvent,
    AuthorEventAttendee,
    AuthorProfile,
    Book,
)

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def author_user(db):
    user = User.objects.create_user(
        username="author_cervantes",
        email="cervantes@example.com",
        password="ValidPassword123!",
    )
    return user


@pytest.fixture
def reader_one(db):
    return User.objects.create_user(
        username="reader_one",
        email="reader1@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def reader_two(db):
    return User.objects.create_user(
        username="reader_two",
        email="reader2@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def author_entity(db, author_user):
    author = Author.objects.create(
        name="Miguel de Cervantes",
        claimed_by=author_user,
        is_verified=True,
    )
    AuthorProfile.objects.create(
        user=author_user,
        author=author,
        pen_name="Miguel de Cervantes Saavedra",
        is_verified=True,
    )
    return author


@pytest.fixture
def sample_book(db, author_entity):
    return Book.objects.create(
        title="Don Quijote de la Mancha",
        author=author_entity,
        isbn="9788424116286",
    )


@pytest.mark.django_db
def test_author_owner_can_create_event(api_client, author_user, author_entity, sample_book):
    api_client.force_authenticate(user=author_user)
    start_time = (timezone.now() + timedelta(days=7)).isoformat()
    end_time = (timezone.now() + timedelta(days=7, hours=2)).isoformat()

    payload = {
        "author": author_entity.id,
        "book": sample_book.id,
        "title": "Presentación de Edición Conmemorativa de Don Quijote",
        "description": "Encuentro literario y firma de ejemplares.",
        "event_type": "BOOK_LAUNCH",
        "event_format": "HYBRID",
        "start_time": start_time,
        "end_time": end_time,
        "location_name": "Ateneo de Madrid / Zoom",
        "location_address": "Calle del Prado 21, Madrid",
        "online_url": "https://meet.jit.si/cervantes-quijote",
        "max_attendees": 50,
    }

    response = api_client.post("/api/v1/books/author-events/", payload, format="json")
    assert response.status_code == status.HTTP_201_CREATED, response.data
    assert response.data["title"] == payload["title"]
    assert response.data["author"] == author_entity.id
    assert response.data["book"] == sample_book.id
    assert response.data["max_attendees"] == 50
    assert AuthorEvent.objects.filter(author=author_entity).count() == 1


@pytest.mark.django_db
def test_unauthorized_user_cannot_create_event_for_author(api_client, reader_one, author_entity):
    api_client.force_authenticate(user=reader_one)
    start_time = (timezone.now() + timedelta(days=3)).isoformat()

    payload = {
        "author": author_entity.id,
        "title": "Evento no autorizado",
        "description": "Intento fraudulento.",
        "start_time": start_time,
    }

    response = api_client.post("/api/v1/books/author-events/", payload, format="json")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "author" in response.data


@pytest.mark.django_db
def test_user_can_register_for_event(api_client, reader_one, author_user, author_entity):
    event = AuthorEvent.objects.create(
        author=author_entity,
        created_by=author_user,
        title="Q&A Literario",
        description="Preguntas sobre la novela picaresca.",
        event_type="QA_SESSION",
        event_format="ONLINE",
        start_time=timezone.now() + timedelta(days=5),
        max_attendees=10,
    )

    api_client.force_authenticate(user=reader_one)
    reg_payload = {"notes": "¿Habrá continuación de la historia?"}
    response = api_client.post(f"/api/v1/books/author-events/{event.id}/register/", reg_payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "REGISTERED"
    assert response.data["is_waitlist"] is False

    attendee = AuthorEventAttendee.objects.get(event=event, user=reader_one)
    assert attendee.status == "REGISTERED"
    assert attendee.notes == "¿Habrá continuación de la historia?"
    assert event.registered_count == 1


@pytest.mark.django_db
def test_capacity_limit_moves_user_to_waitlist(api_client, reader_one, reader_two, author_user, author_entity):
    event = AuthorEvent.objects.create(
        author=author_entity,
        created_by=author_user,
        title="Taller Exclusivo de Narrativa",
        description="Aforo limitado a 1 plaza.",
        start_time=timezone.now() + timedelta(days=2),
        max_attendees=1,
    )

    # Reader one takes the only seat
    api_client.force_authenticate(user=reader_one)
    res1 = api_client.post(f"/api/v1/books/author-events/{event.id}/register/", {}, format="json")
    assert res1.status_code == status.HTTP_201_CREATED
    assert res1.data["status"] == "REGISTERED"

    # Reader two registers and goes to waitlist
    api_client.force_authenticate(user=reader_two)
    res2 = api_client.post(f"/api/v1/books/author-events/{event.id}/register/", {"notes": "Me gustaría mucho asistir."}, format="json")
    assert res2.status_code == status.HTTP_201_CREATED
    assert res2.data["status"] == "WAITLIST"
    assert res2.data["is_waitlist"] is True
    assert event.waitlist_count == 1
    assert event.registered_count == 1


@pytest.mark.django_db
def test_cancelling_registration_promotes_waitlist_user(api_client, reader_one, reader_two, author_user, author_entity):
    event = AuthorEvent.objects.create(
        author=author_entity,
        created_by=author_user,
        title="Sesión Reducida",
        description="Aforo 1.",
        start_time=timezone.now() + timedelta(days=2),
        max_attendees=1,
    )

    # Reader 1 registers
    AuthorEventAttendee.objects.create(event=event, user=reader_one, status="REGISTERED")
    # Reader 2 in waitlist
    AuthorEventAttendee.objects.create(event=event, user=reader_two, status="WAITLIST")

    # Reader 1 cancels
    api_client.force_authenticate(user=reader_one)
    res = api_client.post(f"/api/v1/books/author-events/{event.id}/cancel_registration/", {}, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["status"] == "CANCELLED"
    assert res.data["promoted_user"] == reader_two.username

    # Verify Reader 2 is now REGISTERED
    att2 = AuthorEventAttendee.objects.get(event=event, user=reader_two)
    assert att2.status == "REGISTERED"
    assert event.registered_count == 1
    assert event.waitlist_count == 0


@pytest.mark.django_db
def test_author_can_view_attendees_with_notes(api_client, reader_one, author_user, author_entity):
    event = AuthorEvent.objects.create(
        author=author_entity,
        created_by=author_user,
        title="Firma y Charla",
        description="Charla y preguntas.",
        start_time=timezone.now() + timedelta(days=4),
    )
    AuthorEventAttendee.objects.create(
        event=event,
        user=reader_one,
        status="REGISTERED",
        notes="¿Dedicarás el libro a mi club de lectura?",
    )

    api_client.force_authenticate(user=author_user)
    res = api_client.get(f"/api/v1/books/author-events/{event.id}/attendees/")
    assert res.status_code == status.HTTP_200_OK
    assert len(res.data) == 1
    assert res.data[0]["username"] == reader_one.username
    assert res.data[0]["notes"] == "¿Dedicarás el libro a mi club de lectura?"


@pytest.mark.django_db
def test_filtering_events_by_upcoming_and_author(api_client, author_user, author_entity):
    now = timezone.now()
    past_event = AuthorEvent.objects.create(
        author=author_entity,
        created_by=author_user,
        title="Evento Pasado",
        description="Ya acontecido.",
        start_time=now - timedelta(days=10),
    )
    future_event = AuthorEvent.objects.create(
        author=author_entity,
        created_by=author_user,
        title="Evento Futuro",
        description="Por celebrarse.",
        start_time=now + timedelta(days=10),
    )

    res = api_client.get(f"/api/v1/books/author-events/?author={author_entity.id}&upcoming=true")
    assert res.status_code == status.HTTP_200_OK
    data = res.data.get("results", res.data) if isinstance(res.data, dict) else res.data
    titles = [ev["title"] for ev in data]
    assert "Evento Futuro" in titles
    assert "Evento Pasado" not in titles

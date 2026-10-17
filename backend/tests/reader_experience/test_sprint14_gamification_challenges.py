import datetime
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.gamification_models import (
    Badge,
    BadgeCategory,
    ChallengeType,
    DailyReadingLog,
    ReadingChallenge,
    ReadingGoal,
    ReadingStreak,
    UserBadge,
    UserChallenge,
)
from books.models import Author, Book, ReadingStatus, UserBook

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        username="lector_gamificado",
        email="gamer@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def author_and_books(db):
    author = Author.objects.create(name="Julio Cortázar")
    book1 = Book.objects.create(title="Rayuela", author=author, isbn="9788437604572")
    book2 = Book.objects.create(title="Bestiario", author=author, isbn="9788437601111")
    return author, [book1, book2]


@pytest.mark.django_db
def test_annual_reading_goal_creation_and_pacing_calculation(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    current_year = timezone.now().year

    # 1. Definir meta anual
    payload = {
        "year": current_year,
        "target_books": 24,
        "target_pages": 6000,
    }
    response = api_client.post("/api/v1/gamification/goals/", payload, format="json")
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED), response.data
    assert response.data["goal"]["target_books"] == 24

    # 2. Consultar cálculo de ritmo
    get_res = api_client.get(f"/api/v1/gamification/goals/?year={current_year}")
    assert get_res.status_code == status.HTTP_200_OK, get_res.data
    assert get_res.data["year"] == current_year
    assert get_res.data["target_books"] == 24
    assert get_res.data["has_goal"] is True
    assert "pacing_status" in get_res.data


@pytest.mark.django_db
def test_daily_reading_log_and_streak_accumulation(api_client, test_user, author_and_books):
    api_client.force_authenticate(user=test_user)
    _, books = author_and_books
    today = timezone.now().date()
    yesterday = today - datetime.timedelta(days=1)

    # 1. Registrar lectura de ayer
    payload_yesterday = {
        "date": str(yesterday),
        "pages_read": 30,
        "minutes_read": 45,
        "book_id": books[0].id,
    }
    res1 = api_client.post("/api/v1/gamification/log/", payload_yesterday, format="json")
    assert res1.status_code == status.HTTP_200_OK, res1.data
    assert res1.data["current_streak"] == 1

    # 2. Registrar lectura de hoy (la racha aumenta a 2)
    payload_today = {
        "date": str(today),
        "pages_read": 50,
        "minutes_read": 60,
        "book_id": books[1].id,
    }
    res2 = api_client.post("/api/v1/gamification/log/", payload_today, format="json")
    assert res2.status_code == status.HTTP_200_OK, res2.data
    assert res2.data["current_streak"] == 2
    assert res2.data["longest_streak"] >= 2


@pytest.mark.django_db
def test_join_and_leave_reading_challenge(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    year = timezone.now().year
    challenge = ReadingChallenge.objects.create(
        slug=f"reto-prueba-{year}",
        title="Reto de Primavera",
        description="Lee 5 libros en primavera",
        challenge_type=ChallengeType.BOOKS_COUNT,
        target_count=5,
        start_date=datetime.date(year, 1, 1),
        end_date=datetime.date(year, 12, 31),
        is_active=True,
    )

    # 1. Unirse al reto
    join_res = api_client.post(f"/api/v1/gamification/challenges/{challenge.slug}/join/", format="json")
    assert join_res.status_code == status.HTTP_201_CREATED, join_res.data
    assert join_res.data["challenge_title"] == challenge.title
    assert UserChallenge.objects.filter(user=test_user, challenge=challenge).exists()

    # 2. Abandonar el reto
    leave_res = api_client.post(f"/api/v1/gamification/challenges/{challenge.slug}/leave/", format="json")
    assert leave_res.status_code == status.HTTP_200_OK, leave_res.data
    assert not UserChallenge.objects.filter(user=test_user, challenge=challenge).exists()


@pytest.mark.django_db
def test_automatic_challenge_progress_sync_and_badge_award(api_client, test_user, author_and_books):
    api_client.force_authenticate(user=test_user)
    _, books = author_and_books
    year = timezone.now().year

    # Crear insignia recompensa
    reward_badge, _ = Badge.objects.get_or_create(
        slug="insignia-super-reto",
        defaults={
            "name": "Super Reto Superado",
            "description": "Completaste el reto",
            "icon": "🏆",
            "category": BadgeCategory.CHALLENGES,
            "points": 50,
        },
    )

    # Crear reto de 2 libros
    challenge = ReadingChallenge.objects.create(
        slug=f"reto-duo-{year}",
        title="Reto de dos obras maestras",
        description="Termina 2 libros este año",
        challenge_type=ChallengeType.BOOKS_COUNT,
        target_count=2,
        start_date=datetime.date(year, 1, 1),
        end_date=datetime.date(year, 12, 31),
        badge_reward=reward_badge,
        is_active=True,
    )

    # El usuario se inscribe
    api_client.post(f"/api/v1/gamification/challenges/{challenge.slug}/join/", format="json")

    # El usuario lee 2 libros
    for book in books:
        UserBook.objects.create(
            user=test_user,
            book=book,
            status=ReadingStatus.READ,
            finished_at=timezone.now(),
        )

    # Consultar retos activos (debe sincronizar y completar automáticamente)
    res = api_client.get("/api/v1/gamification/challenges/")
    assert res.status_code == status.HTTP_200_OK, res.data

    user_ch = UserChallenge.objects.get(user=test_user, challenge=challenge)
    assert user_ch.current_progress == 2
    assert user_ch.is_completed is True
    assert user_ch.completed_at is not None

    # Verificar que se otorgó la insignia
    assert UserBadge.objects.filter(user=test_user, badge=reward_badge).exists()


@pytest.mark.django_db
def test_badge_catalog_and_category_filtering(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    res = api_client.get("/api/v1/gamification/badges/")
    assert res.status_code == status.HTTP_200_OK, res.data
    badges = res.data
    assert len(badges) >= 5

    categories = {b["category"] for b in badges}
    assert "reading" in categories
    assert "streak" in categories


@pytest.mark.django_db
def test_gamification_overview_endpoint(api_client, test_user):
    api_client.force_authenticate(user=test_user)
    res = api_client.get("/api/v1/gamification/overview/")
    assert res.status_code == status.HTTP_200_OK, res.data
    assert res.data["gamification_enabled"] is True
    assert "streak" in res.data
    assert "goal" in res.data
    assert "badges" in res.data
    assert "challenges" in res.data


@pytest.mark.django_db
def test_gamification_disabled_preference_toggle(api_client, test_user):
    api_client.force_authenticate(user=test_user)

    # Desactivar gamificación
    patch_res = api_client.patch("/api/v1/gamification/preferences/", {"gamification_enabled": False}, format="json")
    assert patch_res.status_code == status.HTTP_200_OK, patch_res.data
    assert patch_res.data["gamification_enabled"] is False

    # Overview debe reflejar que está desactivada
    res = api_client.get("/api/v1/gamification/overview/")
    assert res.status_code == status.HTTP_200_OK, res.data
    assert res.data["gamification_enabled"] is False

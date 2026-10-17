"""
Tests para Sprint 15: Estadísticas Avanzadas de Lectura, Ritmo, Desglose Temporal y Memoria Anual.
"""

import datetime
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
import pytest
from rest_framework.test import APIClient

from books.cache_utils import user_stats_key
from books.models import Author, Book, Category, ReadingStatus, Review, UserBook
from books.services.stats_service import get_user_reading_stats

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_redis_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def stats_user(db):
    user = User.objects.create_user(
        username="lector_voraz",
        email="lector@example.com",
        password="Password123!",
    )
    user.privacy_level = "public"
    user.save()
    return user


@pytest.fixture
def library_setup(db, stats_user):
    author_a = Author.objects.create(name="Brandon Sanderson")
    author_b = Author.objects.create(name="Jane Austen")

    cat_fantasy = Category.objects.create(name="Fantasía Épica", slug="fantasia-epica")
    cat_romance = Category.objects.create(name="Romance Clásico", slug="romance-clasico")

    # Libro 1: Épico (1000 pág), leído en 10 días en 2026
    book1 = Book.objects.create(
        title="El Camino de los Reyes",
        author=author_a,
    )
    book1.categories.add(cat_fantasy)

    # Libro 2: Corto (150 pág), digital, leído en 2 días en 2026
    book2 = Book.objects.create(
        title="Orgullo y Prejuicio",
        author=author_b,
    )
    book2.categories.add(cat_romance)

    # Libro 3: Medio (350 pág), leído en 2025
    book3 = Book.objects.create(
        title="Nacidos de la Bruma",
        author=author_a,
    )
    book3.categories.add(cat_fantasy)

    # UserBooks
    # ub1: 2026, 1000 pág, 10 días, calificación 5, físico, owned
    ub1 = UserBook.objects.create(
        user=stats_user,
        book=book1,
        status=ReadingStatus.READ,
        is_read=True,
        progress=100,
        current_page=1000,
        started_at=datetime.date(2026, 1, 1),
        finished_at=datetime.date(2026, 1, 10),
        rating=5,
        is_digital=False,
        owned=True,
    )

    # ub2: 2026, 150 pág, 2 días, calificación 4, digital, prestado
    ub2 = UserBook.objects.create(
        user=stats_user,
        book=book2,
        status=ReadingStatus.READ,
        is_read=True,
        progress=100,
        current_page=150,
        started_at=datetime.date(2026, 2, 1),
        finished_at=datetime.date(2026, 2, 2),
        rating=4,
        is_digital=True,
        owned=False,
    )

    # ub3: 2025, 350 pág, 5 días, calificación 5, físico, owned
    ub3 = UserBook.objects.create(
        user=stats_user,
        book=book3,
        status=ReadingStatus.READ,
        is_read=True,
        progress=100,
        current_page=350,
        started_at=datetime.date(2025, 5, 1),
        finished_at=datetime.date(2025, 5, 5),
        rating=5,
        is_digital=False,
        owned=True,
    )

    return {
        "author_a": author_a,
        "author_b": author_b,
        "book1": book1,
        "book2": book2,
        "book3": book3,
        "ub1": ub1,
        "ub2": ub2,
        "ub3": ub3,
    }


@pytest.mark.django_db
class TestSprint15AdvancedReadingStats:

    def test_get_user_reading_stats_basic_and_compatibility(self, stats_user, library_setup):
        """Verifica compatibilidad con claves base existentes en get_user_reading_stats."""
        stats = get_user_reading_stats(stats_user.id)

        assert stats["total_books"] == 3
        assert stats["total_read"] == 3
        assert stats["total_pages_read"] == 1500
        assert stats["average_rating"] == 4.67
        assert stats["books_this_year"] == 2
        assert len(stats["books_per_month"]) == 12
        assert "available_years" in stats
        assert 2026 in stats["available_years"]
        assert 2025 in stats["available_years"]

    def test_reading_pace_metrics(self, stats_user, library_setup):
        """Verifica el cálculo de días por libro, libro más veloz y páginas/día."""
        # 2026 tiene ub1 (10 días) y ub2 (2 días) -> promedio (10 + 2) / 2 = 6.0 días
        stats_2026 = get_user_reading_stats(stats_user.id, year=2026)
        pace = stats_2026["reading_pace"]

        assert pace["avg_days_per_book"] == 6.0
        assert pace["fastest_book"]["title"] == "Orgullo y Prejuicio"
        assert pace["fastest_book"]["days"] == 2
        assert pace["slowest_book"]["title"] == "El Camino de los Reyes"
        assert pace["slowest_book"]["days"] == 10
        assert pace["avg_pages_per_day"] > 0
        assert pace["highest_reading_month"]["count"] >= 1

    def test_length_distribution_and_extremes(self, stats_user, library_setup):
        """Verifica los tramos de páginas (corto, medio, largo, épico) y libros extremos."""
        stats_all = get_user_reading_stats(stats_user.id, year="all")
        lengths = stats_all["length_distribution"]

        # 1 corto (150p), 1 medio (350p), 0 largo, 1 épico (1000p)
        assert lengths["short"]["count"] == 1
        assert lengths["medium"]["count"] == 1
        assert lengths["long"]["count"] == 0
        assert lengths["epic"]["count"] == 1

        assert lengths["longest_book"]["title"] == "El Camino de los Reyes"
        assert lengths["longest_book"]["pages"] == 1000
        assert lengths["shortest_book"]["title"] == "Orgullo y Prejuicio"
        assert lengths["shortest_book"]["pages"] == 150

    def test_format_distribution(self, stats_user, library_setup):
        """Verifica conteo de formatos físico vs digital y posesión."""
        stats = get_user_reading_stats(stats_user.id, year=2026)
        formats = stats["format_distribution"]

        assert formats["physical_count"] == 1
        assert formats["digital_count"] == 1
        assert formats["physical_percentage"] == 50.0
        assert formats["digital_percentage"] == 50.0
        assert formats["owned_count"] == 1
        assert formats["borrowed_count"] == 1

    def test_year_filtering_and_available_years(self, stats_user, library_setup):
        """Verifica filtrado exclusivo por año 2025 frente a histórico general."""
        stats_2025 = get_user_reading_stats(stats_user.id, year=2025)

        assert stats_2025["selected_year"] == 2025
        assert stats_2025["total_read"] == 1
        assert stats_2025["total_pages_read"] == 350
        assert stats_2025["reading_pace"]["avg_days_per_book"] == 5.0
        assert stats_2025["reading_pace"]["fastest_book"]["title"] == "Nacidos de la Bruma"

    def test_year_in_review_and_comparison(self, stats_user, library_setup):
        """Verifica la memoria anual y comparativa frente al año anterior."""
        stats_2026 = get_user_reading_stats(stats_user.id, year=2026)
        yir = stats_2026["year_in_review"]

        assert yir["year"] == 2026
        assert yir["total_books"] == 2
        assert yir["total_pages"] == 1150
        assert yir["highest_rated_book"]["title"] == "El Camino de los Reyes"
        assert yir["highest_rated_book"]["rating"] == 5

        comp = yir["comparison_previous_year"]
        assert comp["previous_year"] == 2025
        assert comp["previous_year_books"] == 1
        assert comp["previous_year_pages"] == 350
        assert comp["books_difference"] == 1
        assert comp["books_percentage_change"] == 100.0

    def test_reading_stats_api_endpoint_with_year_and_privacy(self, stats_user, library_setup):
        """Verifica endpoint GET /api/v1/books/statistics/ con parámetro ?year y control de privacidad."""
        client = APIClient()

        # 1. Petición pública con query param ?year=2026
        resp = client.get(f"/api/v1/books/statistics/?user_id={stats_user.id}&year=2026")
        assert resp.status_code == 200
        data = resp.json()
        assert data["selected_year"] == 2026
        assert data["total_read"] == 2
        assert "reading_pace" in data
        assert "year_in_review" in data

        # 2. Perfil privado sin autenticación -> 403 Forbidden
        stats_user.privacy_level = "private"
        stats_user.save()
        resp_private = client.get(f"/api/v1/books/statistics/?user_id={stats_user.id}")
        assert resp_private.status_code == 403

        # 3. Mismo usuario autenticado -> 200 OK
        client.force_authenticate(user=stats_user)
        resp_auth = client.get(f"/api/v1/books/statistics/?user_id={stats_user.id}&year=2026")
        assert resp_auth.status_code == 200

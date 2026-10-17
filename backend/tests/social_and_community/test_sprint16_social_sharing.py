"""
Tests para Sprint 16: Integración con Redes Sociales y Compartición Gráfica.
"""

from django.contrib.auth import get_user_model
from django.core.cache import cache
import pytest
from rest_framework.test import APIClient

from books.models import Badge, Book, Category, ReadingChallenge, ReadingList, ReadingStatus, UserBook, UserChallenge
from books.services.social_share_service import generate_social_share_card, track_social_share

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_redis_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def share_user(db):
    user = User.objects.create_user(
        username="lector_social",
        email="social@example.com",
        password="Password123!",
    )
    user.privacy_level = "public"
    user.save()
    return user


@pytest.fixture
def sample_catalog(db, share_user):
    cat = Category.objects.create(name="Ciencia Ficción", slug="ciencia-ficcion")
    book = Book.objects.create(
        title="Dune",
        average_rating=4.8,
        description="Una obra maestra de la ciencia ficción en el planeta Arrakis.",
    )
    book.categories.add(cat)

    # UserBook para estadísticas
    ub = UserBook.objects.create(
        user=share_user,
        book=book,
        status=ReadingStatus.READ,
        is_read=True,
        current_page=600,
        progress=100,
        rating=5,
    )

    # Reto e Insignia
    badge = Badge.objects.create(
        name="Pionero de Arrakis",
        slug="pionero-arrakis",
        description="Has explorado un clásico de la ciencia ficción.",
        icon="🏜️",
        points=25,
        category="reading",
    )
    import datetime
    challenge = ReadingChallenge.objects.create(
        title="Reto CiFi 2026",
        slug="reto-cifi-2026",
        description="Lee 5 libros de ciencia ficción.",
        target_count=5,
        challenge_type="books_count",
        start_date=datetime.date(2026, 1, 1),
        end_date=datetime.date(2026, 12, 31),
        badge_reward=badge,
    )
    uc = UserChallenge.objects.create(
        user=share_user,
        challenge=challenge,
        current_progress=2,
    )

    # Lista de lectura
    rlist = ReadingList.objects.create(
        user=share_user,
        name="Mis Clásicos Favoritos",
        slug="mis-clasicos-favoritos",
        description="Selección personal de grandes obras.",
    )

    return {
        "book": book,
        "ub": ub,
        "badge": badge,
        "challenge": challenge,
        "uc": uc,
        "rlist": rlist,
    }


@pytest.mark.django_db
class TestSprint16SocialSharing:

    def test_generate_social_share_card_for_book(self, sample_catalog):
        """Verifica la generación de tarjeta y enlaces para libros."""
        book = sample_catalog["book"]
        card = generate_social_share_card("book", object_id=book.id)

        assert card["share_type"] == "book"
        assert card["title"] == "Dune"
        assert "Dune" in card["share_text"]
        assert "@MyBookConnect" in card["share_text"]
        assert "#MyBookConnect" in card["hashtags"]

        # Verificar enlaces directos de compartición
        urls = card["share_urls"]
        assert "twitter.com/intent/tweet" in urls["twitter"]
        assert "api.whatsapp.com/send" in urls["whatsapp"]
        assert "t.me/share/url" in urls["telegram"]
        assert "linkedin.com/sharing/share-offsite" in urls["linkedin"]
        assert "facebook.com/sharer/sharer.php" in urls["facebook"]
        assert "mailto:" in urls["email"]

    def test_generate_social_share_card_for_reading_stats(self, share_user, sample_catalog):
        """Verifica tarjeta para estadísticas de lectura y memoria anual."""
        card = generate_social_share_card("reading_stats", user_id=share_user.id)

        assert card["share_type"] == "reading_stats"
        assert "Memoria Lectora" in card["card_data"]["title"]
        assert "600 páginas" in card["card_data"]["stat_label"]
        assert "@MyBookConnect" in card["share_text"]
        assert "#EstadisticasDeLectura" in card["hashtags"]

    def test_generate_social_share_card_for_challenge(self, share_user, sample_catalog):
        """Verifica tarjeta de reto con progreso del lector."""
        challenge = sample_catalog["challenge"]
        card = generate_social_share_card("challenge", object_id=challenge.slug, user_id=share_user.id)

        assert card["share_type"] == "challenge"
        assert card["title"] == "Reto CiFi 2026"
        assert "Reto CiFi 2026" in card["share_text"]
        assert "(2/5)" in card["share_text"]
        assert "#RetoLiterario" in card["hashtags"]

    def test_generate_social_share_card_for_badge(self, sample_catalog):
        """Verifica tarjeta de logro o medalla."""
        badge = sample_catalog["badge"]
        card = generate_social_share_card("badge", object_id=badge.slug)

        assert card["share_type"] == "badge"
        assert card["title"] == "Pionero de Arrakis"
        assert "+25 pts" in card["card_data"]["stat_highlight"]
        assert "🏜️" in card["card_data"]["badge_or_icon"]
        assert "#LogroLector" in card["hashtags"]

    def test_generate_social_share_card_for_reading_list(self, sample_catalog):
        """Verifica tarjeta para listas de lectura públicas."""
        rlist = sample_catalog["rlist"]
        card = generate_social_share_card("reading_list", object_id=rlist.id)

        assert card["share_type"] == "reading_list"
        assert card["title"] == "Mis Clásicos Favoritos"
        assert "Mis Clásicos Favoritos" in card["share_text"]
        assert "lector_social" in card["card_data"]["subtitle"]

    def test_social_share_card_endpoint_and_invalid_type(self, sample_catalog):
        """Verifica endpoint GET /api/v1/books/share/card/ y respuestas 200 y 400."""
        client = APIClient()
        book = sample_catalog["book"]

        # Éxito: tipo válido
        resp = client.get(f"/api/v1/books/share/card/?type=book&id={book.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_type"] == "book"
        assert data["title"] == "Dune"

        # Error: tipo inválido
        resp_bad = client.get("/api/v1/books/share/card/?type=tipo_desconocido&id=1")
        assert resp_bad.status_code == 400
        assert "no soportado" in resp_bad.json()["detail"]

    def test_social_share_track_endpoint(self, share_user, sample_catalog):
        """Verifica endpoint POST /api/v1/books/share/track/ para auditoría de compartición."""
        client = APIClient()
        client.force_authenticate(user=share_user)
        book = sample_catalog["book"]

        payload = {
            "type": "book",
            "id": book.id,
            "platform": "twitter",
        }
        resp = client.post("/api/v1/books/share/track/", payload, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "tracked"
        assert data["platform"] == "twitter"
        assert data["share_type"] == "book"
        assert data["object_id"] == str(book.id)

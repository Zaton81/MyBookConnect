import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from books.models import Author, Book, ReadingList, Review, UserBook
from users.models import MessagePrivacyChoices, PrivacyChoices
from users.privacy_service import PrivacyService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def privacy_setup(db):
    author = Author.objects.create(name="Gabriel García Márquez")
    book1 = Book.objects.create(title="Cien años de soledad", author=author, isbn="9780307474728")
    book2 = Book.objects.create(title="El amor en los tiempos del cólera", author=author, isbn="9780307389732")
    book3 = Book.objects.create(title="Crónica de una muerte anunciada", author=author, isbn="9781400034956")

    # Usuario Público (u_public)
    u_public = User.objects.create_user(
        username="u_public",
        email="public@example.com",
        password="password123",
        privacy_level=PrivacyChoices.PUBLIC,
        reading_privacy_level=PrivacyChoices.PUBLIC,
        activity_privacy_level=PrivacyChoices.PUBLIC,
        allow_messages_from=MessagePrivacyChoices.EVERYONE,
        location="Madrid",
        bio="Lector público",
        show_email=False,
        show_location=True,
        show_bio=True,
    )

    # Usuario Solo Amigos (u_friends)
    u_friends = User.objects.create_user(
        username="u_friends",
        email="friends@example.com",
        password="password123",
        privacy_level=PrivacyChoices.FRIENDS,
        reading_privacy_level=PrivacyChoices.FRIENDS,
        activity_privacy_level=PrivacyChoices.FRIENDS,
        allow_messages_from=MessagePrivacyChoices.FOLLOWED,
        location="Barcelona",
        bio="Solo amigos",
    )

    # Usuario Privado (u_private)
    u_private = User.objects.create_user(
        username="u_private",
        email="private@example.com",
        password="password123",
        privacy_level=PrivacyChoices.PRIVATE,
        reading_privacy_level=PrivacyChoices.PRIVATE,
        activity_privacy_level=PrivacyChoices.PRIVATE,
        allow_messages_from=MessagePrivacyChoices.NOBODY,
        location="Sevilla",
        bio="Lector privado",
    )

    # Usuario Observador / Seguidor (u_viewer)
    u_viewer = User.objects.create_user(
        username="u_viewer",
        email="viewer@example.com",
        password="password123",
    )

    # Usuario Extraño (u_stranger)
    u_stranger = User.objects.create_user(
        username="u_stranger",
        email="stranger@example.com",
        password="password123",
    )

    # Relación de seguimiento: u_viewer sigue a u_friends
    u_viewer.following.add(u_friends)

    # Biblioteca
    UserBook.objects.create(user=u_public, book=book1, is_read=True, rating=5)
    UserBook.objects.create(user=u_friends, book=book1, is_read=True, rating=5)
    UserBook.objects.create(user=u_private, book=book1, is_read=True, rating=5)
    UserBook.objects.create(user=u_viewer, book=book1, is_read=True, rating=5)
    UserBook.objects.create(user=u_viewer, book=book2, is_read=True, rating=4)

    # Reseñas
    Review.objects.create(user=u_public, book=book1, rating=5, title="Obra maestra", text="Increíble")
    Review.objects.create(user=u_friends, book=book1, rating=4, title="Gran clásico", text="Muy bueno")
    Review.objects.create(user=u_private, book=book1, rating=5, title="Privada", text="Personal")

    # Listas de lectura
    ReadingList.objects.create(user=u_public, name="Lista Pública", privacy="public")
    ReadingList.objects.create(user=u_friends, name="Lista Amigos", privacy="followers")
    ReadingList.objects.create(user=u_private, name="Lista Secreta", privacy="private")

    return {
        "u_public": u_public,
        "u_friends": u_friends,
        "u_private": u_private,
        "u_viewer": u_viewer,
        "u_stranger": u_stranger,
        "book1": book1,
        "book2": book2,
        "book3": book3,
    }


@pytest.mark.django_db
class TestPrivacyCoreService:
    def test_can_view_profile_rules(self, privacy_setup):
        u_pub = privacy_setup["u_public"]
        u_fri = privacy_setup["u_friends"]
        u_priv = privacy_setup["u_private"]
        u_view = privacy_setup["u_viewer"]
        u_str = privacy_setup["u_stranger"]

        # Anónimo
        assert PrivacyService.can_view_profile(None, u_pub) is True
        assert PrivacyService.can_view_profile(None, u_fri) is False
        assert PrivacyService.can_view_profile(None, u_priv) is False

        # u_viewer (sigue a u_friends)
        assert PrivacyService.can_view_profile(u_view, u_pub) is True
        assert PrivacyService.can_view_profile(u_view, u_fri) is True
        assert PrivacyService.can_view_profile(u_view, u_priv) is False

        # u_stranger (no sigue a u_friends)
        assert PrivacyService.can_view_profile(u_str, u_pub) is True
        assert PrivacyService.can_view_profile(u_str, u_fri) is False
        assert PrivacyService.can_view_profile(u_str, u_priv) is False

        # Mismo usuario
        assert PrivacyService.can_view_profile(u_priv, u_priv) is True

    def test_can_view_reading_activity_granular(self, privacy_setup):
        u_pub = privacy_setup["u_public"]
        u_fri = privacy_setup["u_friends"]
        u_priv = privacy_setup["u_private"]
        u_view = privacy_setup["u_viewer"]
        u_str = privacy_setup["u_stranger"]

        # u_public pone reading_privacy_level='private'
        u_pub.reading_privacy_level = PrivacyChoices.PRIVATE
        u_pub.save()
        assert PrivacyService.can_view_reading_activity(u_view, u_pub) is False
        assert PrivacyService.can_view_reading_activity(u_pub, u_pub) is True

        # u_friends: u_view le sigue -> True, u_stranger no le sigue -> False
        assert PrivacyService.can_view_reading_activity(u_view, u_fri) is True
        assert PrivacyService.can_view_reading_activity(u_str, u_fri) is False

        # u_private siempre False para terceros
        assert PrivacyService.can_view_reading_activity(u_view, u_priv) is False

    def test_bidirectional_blocking_and_anti_enumeration(self, api_client, privacy_setup):
        u_pub = privacy_setup["u_public"]
        u_view = privacy_setup["u_viewer"]

        api_client.force_authenticate(user=u_pub)
        # u_pub bloquea a u_view
        res_block = api_client.post(f"/api/v1/users/{u_view.id}/block/")
        assert res_block.status_code == 200

        # Bloqueo mutuo activo
        assert PrivacyService.are_mutually_blocked(u_pub, u_view) is True
        assert PrivacyService.are_mutually_blocked(u_view, u_pub) is True

        # Visor bloqueado intenta acceder a biblioteca de u_pub -> 404 anti-enumeración
        api_client.force_authenticate(user=u_view)
        res_lib = api_client.get(f"/api/v1/books/user/books/?user_id={u_pub.id}")
        assert res_lib.status_code == 404

        # Visor bloqueado intenta calcular Reading Match -> 404 anti-enumeración
        res_match = api_client.get(f"/api/v1/books/match/{u_pub.id}/")
        assert res_match.status_code == 404

    def test_messaging_privacy_permissions(self, privacy_setup):
        u_pub = privacy_setup["u_public"]
        u_fri = privacy_setup["u_friends"]
        u_priv = privacy_setup["u_private"]
        u_view = privacy_setup["u_viewer"]
        u_str = privacy_setup["u_stranger"]

        # u_pub permite mensajes de EVERYONE
        assert PrivacyService.can_message(u_str, u_pub) is True

        # u_fri solo permite de personas que sigue o le siguen (FOLLOWED)
        assert PrivacyService.can_message(u_view, u_fri) is True
        assert PrivacyService.can_message(u_str, u_fri) is False

        # u_priv no permite de nadie (NOBODY)
        assert PrivacyService.can_message(u_view, u_priv) is False
        assert PrivacyService.can_message(u_str, u_priv) is False

    def test_profile_field_redaction(self, api_client, privacy_setup):
        u_pub = privacy_setup["u_public"]
        u_str = privacy_setup["u_stranger"]

        api_client.force_authenticate(user=u_str)
        res = api_client.get(f"/api/v1/users/{u_pub.id}/")
        assert res.status_code == 200
        data = res.data

        # Email oculto porque show_email=False
        assert data.get("email") == ""
        # Configuración interna privada eliminada del payload
        assert "allow_messages_from" not in data
        assert "reading_privacy_level" not in data
        assert "activity_privacy_level" not in data

    def test_reading_match_with_private_library(self, api_client, privacy_setup):
        u_priv = privacy_setup["u_private"]
        u_view = privacy_setup["u_viewer"]

        api_client.force_authenticate(user=u_view)
        res = api_client.get(f"/api/v1/books/match/{u_priv.id}/")
        # u_priv tiene biblioteca privada -> 403 Forbidden
        assert res.status_code == 403

    def test_filter_visible_reading_lists_privacy(self, privacy_setup):
        u_view = privacy_setup["u_viewer"]
        u_str = privacy_setup["u_stranger"]

        visible_for_viewer = PrivacyService.filter_visible_reading_lists(
            u_view, ReadingList.objects.all()
        ).values_list("name", flat=True)

        assert "Lista Pública" in visible_for_viewer
        assert "Lista Amigos" in visible_for_viewer  # porque u_view sigue a u_friends
        assert "Lista Secreta" not in visible_for_viewer

        visible_for_stranger = PrivacyService.filter_visible_reading_lists(
            u_str, ReadingList.objects.all()
        ).values_list("name", flat=True)

        assert "Lista Pública" in visible_for_stranger
        assert "Lista Amigos" not in visible_for_stranger  # u_stranger no sigue a u_friends
        assert "Lista Secreta" not in visible_for_stranger

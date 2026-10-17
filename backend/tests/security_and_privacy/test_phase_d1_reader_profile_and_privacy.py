"""
Suite integral de pruebas para la Fase D1 (Perfil de Lector y Privacidad) del Roadmap v2.0.

Cubre:
1. Consistencia de perfil público, privado y solo amigos en la API.
2. Ofuscación de datos personales (email, cumpleaños, ubicación, bio) según preferencias granulares.
3. Aislamiento y consecuencias de bloqueos bidireccionales (auto-unfollow, acceso restringido, mensajería).
4. Protección de estadísticas y biblioteca bajo `reading_privacy_level`.
5. Re-validación del circuito RGPD (Art. 17 Supresión y Art. 20 Portabilidad) bajo la marca My Book Social.
"""

import json
from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book, ReadingStatus, Review, UserBook
from users.models import AuditAction, AuditLog, PrivacyChoices
from users.privacy_service import PrivacyService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_users(db):
    alice = User.objects.create_user(
        username="alice_reader",
        email="alice@mybooksocial.com",
        password="Password123!",
        first_name="Alice",
        last_name="Wonder",
        bio="Apasionada de la ciencia ficción y la fantasía.",
        location="Madrid, España",
        birth_date=date(1995, 5, 20),
        privacy_level=PrivacyChoices.PUBLIC,
        reading_privacy_level=PrivacyChoices.PUBLIC,
        activity_privacy_level=PrivacyChoices.PUBLIC,
        show_email=False,
        show_birth_date=False,
        show_location=True,
        show_bio=True,
    )

    bob = User.objects.create_user(
        username="bob_reader",
        email="bob@mybooksocial.com",
        password="Password123!",
        first_name="Bob",
        last_name="Builder",
        bio="Lector casual de ensayos.",
        location="Barcelona, España",
        privacy_level=PrivacyChoices.FRIENDS,
        reading_privacy_level=PrivacyChoices.FRIENDS,
        activity_privacy_level=PrivacyChoices.FRIENDS,
    )

    charlie = User.objects.create_user(
        username="charlie_private",
        email="charlie@mybooksocial.com",
        password="Password123!",
        first_name="Charlie",
        last_name="Chaplin",
        bio="Lector anónimo y reservado.",
        privacy_level=PrivacyChoices.PRIVATE,
        reading_privacy_level=PrivacyChoices.PRIVATE,
        activity_privacy_level=PrivacyChoices.PRIVATE,
    )

    admin = User.objects.create_superuser(
        username="admin_ops",
        email="admin@mybooksocial.com",
        password="AdminPassword123!",
    )

    return {"alice": alice, "bob": bob, "charlie": charlie, "admin": admin}


@pytest.mark.django_db
class TestProfileVisibilityAndFieldMasking:
    def test_public_profile_masks_hidden_pii_for_strangers(self, api_client, test_users):
        """Un usuario ajeno no debe ver email ni fecha de nacimiento si las flags están en False."""
        alice = test_users["alice"]
        bob = test_users["bob"]

        api_client.force_authenticate(user=bob)
        response = api_client.get(f"/api/v1/users/{alice.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["username"] == "alice_reader"
        # Flags show_email y show_birth_date están en False -> campos ofuscados
        assert data.get("email") in ("", None)
        assert data.get("birth_date") is None
        # Flags show_location y show_bio están en True -> visibles
        assert data.get("location") == "Madrid, España"
        assert "ciencia ficción" in data.get("bio", "")

    def test_user_can_view_own_complete_profile_unmasked(self, api_client, test_users):
        """El propio usuario autenticado siempre ve todos sus datos personales sin ofuscación."""
        alice = test_users["alice"]

        api_client.force_authenticate(user=alice)
        response = api_client.get(f"/api/v1/users/{alice.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["email"] == "alice@mybooksocial.com"
        assert str(data["birth_date"]) == "1995-05-20"
        assert data["location"] == "Madrid, España"
        assert "ciencia ficción" in data["bio"]

    def test_friends_only_profile_access_control(self, api_client, test_users):
        """Perfil con privacy_level='friends' deniega acceso antes de follow y lo permite tras follow."""
        bob = test_users["bob"]  # privacy_level = 'friends'
        alice = test_users["alice"]

        api_client.force_authenticate(user=alice)

        # 1. Antes de seguir -> 403 Forbidden
        denied_res = api_client.get(f"/api/v1/users/{bob.id}/")
        assert denied_res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

        # 2. Alice sigue a Bob
        follow_res = api_client.post(f"/api/v1/users/{bob.id}/follow/")
        assert follow_res.status_code == status.HTTP_200_OK
        assert alice.following.filter(id=bob.id).exists()

        # 3. Tras seguir -> 200 OK
        allowed_res = api_client.get(f"/api/v1/users/{bob.id}/")
        assert allowed_res.status_code == status.HTTP_200_OK
        assert allowed_res.data["username"] == "bob_reader"

    def test_private_profile_denies_all_except_self_and_staff(self, api_client, test_users):
        """Perfil privado solo es accesible por el dueño y por administradores."""
        charlie = test_users["charlie"]  # privacy_level = 'private'
        alice = test_users["alice"]
        admin = test_users["admin"]

        # 1. Tercero autenticado -> 403
        api_client.force_authenticate(user=alice)
        res_stranger = api_client.get(f"/api/v1/users/{charlie.id}/")
        assert res_stranger.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

        # 2. El propio dueño -> 200
        api_client.force_authenticate(user=charlie)
        res_self = api_client.get(f"/api/v1/users/{charlie.id}/")
        assert res_self.status_code == status.HTTP_200_OK
        assert res_self.data["username"] == "charlie_private"

        # 3. Administrador de la plataforma -> 200
        api_client.force_authenticate(user=admin)
        res_admin = api_client.get(f"/api/v1/users/{charlie.id}/")
        assert res_admin.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestBlockingAndIsolation:
    def test_block_action_auto_unfollows_and_blocks_bidirectionally(self, api_client, test_users):
        """El bloqueo de usuario disuelve el follow mutuo y restringe el acceso al perfil."""
        alice = test_users["alice"]
        bob = test_users["bob"]

        # Alice sigue a Bob y Bob sigue a Alice
        alice.following.add(bob)
        bob.following.add(alice)
        assert alice.following.filter(id=bob.id).exists()
        assert bob.following.filter(id=alice.id).exists()

        # Alice bloquea a Bob
        api_client.force_authenticate(user=alice)
        block_res = api_client.post(f"/api/v1/users/{bob.id}/block/")
        assert block_res.status_code == status.HTTP_200_OK
        assert alice.blocked_users.filter(id=bob.id).exists()

        # Auto-unfollow verificado
        assert not alice.following.filter(id=bob.id).exists()

        # Bob intenta acceder al perfil de Alice -> Denegado
        api_client.force_authenticate(user=bob)
        denied_res = api_client.get(f"/api/v1/users/{alice.id}/")
        assert denied_res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

        # Evaluación en PrivacyService
        assert PrivacyService.are_mutually_blocked(alice, bob)
        assert not PrivacyService.can_message(bob, alice)
        assert not PrivacyService.can_interact(bob, alice)


@pytest.mark.django_db
class TestReadingPrivacyAndStatsProtection:
    def test_reading_privacy_level_masks_stats_for_public_profile(self, api_client, test_users):
        """Si un usuario tiene perfil público pero reading_privacy='private', sus estadísticas se ofuscan a 0."""
        alice = test_users["alice"]
        bob = test_users["bob"]

        # Alice añade 2 libros y una reseña
        book1 = Book.objects.create(title="Dune", isbn="9780441172719")
        book2 = Book.objects.create(title="Neuromante", isbn="9780441569595")
        UserBook.objects.create(user=alice, book=book1, status=ReadingStatus.READ)
        UserBook.objects.create(user=alice, book=book2, status=ReadingStatus.READING)
        Review.objects.create(user=alice, book=book1, rating=5, text="Obra maestra")

        # Alice cambia reading_privacy_level a PRIVATE
        alice.reading_privacy_level = PrivacyChoices.PRIVATE
        alice.save()

        # Bob visita el perfil de Alice
        api_client.force_authenticate(user=bob)
        response = api_client.get(f"/api/v1/users/{alice.id}/")
        assert response.status_code == status.HTTP_200_OK

        # Las estadísticas de lectura deben mostrarse en 0 para Bob
        assert response.data.get("books_read_count", 0) == 0
        assert response.data.get("reviews_count", 0) == 0


@pytest.mark.django_db
class TestGDPRComplianceMyBookSocial:
    def test_gdpr_data_export_mybooksocial_format(self, api_client, test_users):
        """Verifica que la exportación de datos RGPD use el nombre y metadatos de My Book Social."""
        alice = test_users["alice"]
        book = Book.objects.create(title="Fahrenheit 451", isbn="9781451673319")
        UserBook.objects.create(user=alice, book=book, status=ReadingStatus.READING, current_page=50)

        api_client.force_authenticate(user=alice)
        response = api_client.get("/api/v1/users/account/export/")

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response["Content-Type"]

        # Nombre de archivo estandarizado con la marca My Book Social
        content_disposition = response["Content-Disposition"]
        assert f'filename="mybooksocial_data_export_{alice.username}.json"' in content_disposition

        # Payload parseado
        data = json.loads(response.content.decode("utf-8"))
        assert data["_metadata"]["platform"] == "My Book Social"
        assert data["_metadata"]["user_id"] == alice.id
        assert data["profile"]["username"] == "alice_reader"
        assert len(data["library"]) == 1
        assert data["library"][0]["book_title"] == "Fahrenheit 451"

        # AuditLog generado
        audit = AuditLog.objects.filter(actor=alice, action=AuditAction.DATA_EXPORT).first()
        assert audit is not None

    def test_gdpr_account_deletion_anonymization(self, api_client, test_users):
        """Verifica que la eliminación de cuenta anonimice PII y desactive la cuenta conforme al RGPD."""
        bob = test_users["bob"]
        bob_id = bob.id

        api_client.force_authenticate(user=bob)
        payload = {
            "password": "Password123!",
            "confirmation": "ELIMINAR",
        }
        response = api_client.post("/api/v1/users/account/delete/", payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["deleted"] is True

        bob.refresh_from_db()
        assert not bob.is_active
        assert bob.deleted_at is not None
        assert bob.username.startswith("deleted_user_")
        assert bob.email.endswith("@deleted.local")
        assert bob.bio == ""
        assert not bob.has_usable_password()

        # AuditLog generado
        audit = AuditLog.objects.filter(action=AuditAction.USER_DELETE, object_id=bob_id).first()
        assert audit is not None

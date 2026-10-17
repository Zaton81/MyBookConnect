import json
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import (
    Book,
    ReadingList,
    ReadingListPrivacy,
    ReadingStatus,
    Review,
    ReviewComment,
    UserBook,
)
from users.models import AuditAction, AuditLog

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    user = User.objects.create_user(
        username="privacyuser",
        email="privacy@example.com",
        password="ValidPassword123!",
        first_name="Privacy",
        last_name="Tester",
        bio="Test bio description",
        terms_accepted_at=timezone.now(),
        privacy_accepted_at=timezone.now(),
    )
    return user


@pytest.fixture
def other_user(db):
    user = User.objects.create_user(
        username="otheruser",
        email="other@example.com",
        password="OtherPassword123!",
    )
    return user


@pytest.mark.django_db
class TestEmailChange:
    def test_email_change_success(self, api_client, regular_user):
        api_client.force_authenticate(user=regular_user)
        url = "/api/v1/users/email/change/"
        payload = {
            "new_email": "newprivacy@example.com",
            "current_password": "ValidPassword123!",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "actualizado correctamente" in response.data["detail"]
        assert response.data["email"] == "newprivacy@example.com"

        regular_user.refresh_from_db()
        assert regular_user.email == "newprivacy@example.com"

        # Comprobar log de auditoría
        audit = AuditLog.objects.filter(actor=regular_user, action=AuditAction.EMAIL_CHANGE).first()
        assert audit is not None
        assert audit.metadata.get("new_email") == "newprivacy@example.com"

    def test_email_change_invalid_password(self, api_client, regular_user):
        api_client.force_authenticate(user=regular_user)
        url = "/api/v1/users/email/change/"
        payload = {
            "new_email": "brandnew@example.com",
            "current_password": "WrongPassword!",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "incorrecta" in response.data.get("detail", "").lower()

        regular_user.refresh_from_db()
        assert regular_user.email == "privacy@example.com"

    def test_email_change_duplicate_email(self, api_client, regular_user, other_user):
        api_client.force_authenticate(user=regular_user)
        url = "/api/v1/users/email/change/"
        payload = {
            "new_email": "other@example.com",
            "current_password": "ValidPassword123!",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "registrada" in response.data.get("detail", "").lower()

        regular_user.refresh_from_db()
        assert regular_user.email == "privacy@example.com"


@pytest.mark.django_db
class TestAccountDeletion:
    def test_account_deletion_success_and_anonymization(self, api_client, regular_user, other_user):
        user_id = regular_user.id
        # Crear relaciones e historial para regular_user
        regular_user.following.add(other_user)
        other_user.following.add(regular_user)
        regular_user.blocked_users.add(other_user)

        # Crear lista de lectura
        r_list = ReadingList.objects.create(
            user=regular_user,
            name="Mis favoritos",
            privacy=ReadingListPrivacy.PUBLIC,
            is_moderated=False,
        )

        # Crear libro y comentario en reseña
        book = Book.objects.create(title="Libro Privacidad", isbn="9780000000017")
        review = Review.objects.create(user=other_user, book=book, rating=4, text="Gran libro")
        comment = ReviewComment.objects.create(user=regular_user, review=review, content="Buen punto")

        api_client.force_authenticate(user=regular_user)
        url = "/api/v1/users/account/delete/"
        payload = {
            "password": "ValidPassword123!",
            "confirmation": "ELIMINAR",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK

        regular_user.refresh_from_db()
        assert not regular_user.is_active
        assert regular_user.deleted_at is not None
        assert regular_user.username.startswith("deleted_user_")
        assert regular_user.email.endswith("@deleted.local")
        assert regular_user.first_name == ""
        assert regular_user.last_name == ""
        assert regular_user.bio == ""
        assert not regular_user.has_usable_password()

        # Comprobar desvinculaciones sociales
        assert not regular_user.following.exists()
        assert not regular_user.followers.exists()
        assert not regular_user.blocked_users.exists()

        # Comprobar listas de lectura
        r_list.refresh_from_db()
        assert r_list.privacy == ReadingListPrivacy.PRIVATE
        assert r_list.is_moderated

        # Comprobar soft-delete de comentarios
        comment.refresh_from_db()
        assert comment.is_deleted

        # Comprobar AuditLog
        audit = AuditLog.objects.filter(action=AuditAction.USER_DELETE, object_id=user_id).first()
        if not audit:
            audit = AuditLog.objects.filter(action=AuditAction.USER_DELETE).first()
        assert audit is not None
        assert audit.metadata.get("original_user_id") == user_id

    def test_account_deletion_invalid_confirmation(self, api_client, regular_user):
        api_client.force_authenticate(user=regular_user)
        url = "/api/v1/users/account/delete/"
        payload = {
            "password": "ValidPassword123!",
            "confirmation": "NO_QUIERO",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirmación" in response.data.get("detail", "").lower()

        regular_user.refresh_from_db()
        assert regular_user.is_active

    def test_prevent_deleting_last_superuser(self, api_client, db):
        admin = User.objects.create_superuser(
            username="soloadmin",
            email="admin@example.com",
            password="AdminPassword123!",
        )
        api_client.force_authenticate(user=admin)
        url = "/api/v1/users/account/delete/"
        payload = {
            "password": "AdminPassword123!",
            "confirmation": "ELIMINAR",
        }

        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "único superadministrador" in response.data.get("detail", "")

        admin.refresh_from_db()
        assert admin.is_active


@pytest.mark.django_db
class TestDataExport:
    def test_data_export_json_payload(self, api_client, regular_user, other_user):
        # Preparar libros y listas para enriquecer la exportación
        book = Book.objects.create(title="Libro de datos", isbn="9780000000024")
        UserBook.objects.create(user=regular_user, book=book, status=ReadingStatus.READING)
        Review.objects.create(user=regular_user, book=book, rating=5, text="Excelente")
        ReadingList.objects.create(user=regular_user, name="Mi lista exportable", privacy=ReadingListPrivacy.PUBLIC)
        regular_user.following.add(other_user)

        api_client.force_authenticate(user=regular_user)
        url = "/api/v1/users/account/export/"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response["Content-Type"]
        assert "attachment; filename=" in response["Content-Disposition"]

        content = json.loads(response.content.decode("utf-8"))
        assert "_metadata" in content
        assert "profile" in content
        assert content["profile"]["username"] == regular_user.username
        assert content["profile"]["email"] == regular_user.email
        assert "library" in content
        assert len(content["library"]) == 1
        assert len(content["reviews"]) == 1
        assert len(content["reading_lists"]) == 1
        assert len(content["social"]["following"]) == 1

        # AuditLog
        audit = AuditLog.objects.filter(actor=regular_user, action=AuditAction.DATA_EXPORT).first()
        assert audit is not None

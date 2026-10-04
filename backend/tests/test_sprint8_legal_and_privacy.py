import json
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import Book, LegalDocument, Review, UserBook
from users.models import Report

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username="lector_rgpd",
        email="rgpd_user@example.com",
        password="ValidPassword123!",
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="admin_legal",
        email="legal_admin@example.com",
        password="AdminPassword123!",
    )


@pytest.fixture
def seed_docs(db):
    LegalDocument.objects.update_or_create(
        slug="terms",
        defaults={
            "title": "Términos y Condiciones de Uso",
            "content": "# Términos de Uso oficiales de la plataforma.",
        },
    )
    LegalDocument.objects.update_or_create(
        slug="privacy",
        defaults={
            "title": "Política de Privacidad y RGPD",
            "content": "# Política de Privacidad conforme al Reglamento General de Protección de Datos.",
        },
    )
    LegalDocument.objects.update_or_create(
        slug="cookies",
        defaults={
            "title": "Política de Cookies",
            "content": "# Información sobre cookies técnicas y analíticas.",
        },
    )


@pytest.mark.django_db
class TestSprint8LegalAndPrivacy:
    """
    Suite de pruebas de integración para la Sección 26 de RoadmapV3:
    Legalidad, Documentos Normativos, Portabilidad de Datos RGPD y Cancelación/Eliminación de Cuenta.
    """

    def test_public_legal_documents_list_and_detail(self, api_client, seed_docs):
        """1. Consulta pública de documentos legales (términos, privacidad, cookies)."""
        # Listado público
        res_list = api_client.get("/api/v1/books/legal/")
        assert res_list.status_code == status.HTTP_200_OK
        docs = res_list.json()
        slugs = [d["slug"] for d in docs]
        assert "terms" in slugs
        assert "privacy" in slugs
        assert "cookies" in slugs

        # Detalle de privacidad
        res_priv = api_client.get("/api/v1/books/legal/privacy/")
        assert res_priv.status_code == status.HTTP_200_OK
        assert "Privacidad" in res_priv.json()["title"]

        # Detalle de términos
        res_terms = api_client.get("/api/v1/books/legal/terms/")
        assert res_terms.status_code == status.HTTP_200_OK
        assert "Términos" in res_terms.json()["title"]

        # Documento inexistente
        res_404 = api_client.get("/api/v1/books/legal/documento_ficticio/")
        assert res_404.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_legal_documents_update(self, api_client, admin_user, regular_user, seed_docs):
        """2. Edición administrativa de documentos normativos."""
        # Usuario no administrador denegado
        refresh_user = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_user.access_token}")
        res_denied = api_client.put(
            "/api/v1/admin/legal/terms/",
            {"title": "Términos Hackeados", "content": "Texto modificado"},
            format="json",
        )
        assert res_denied.status_code == status.HTTP_403_FORBIDDEN

        # Administrador autorizado
        refresh_admin = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_admin.access_token}")
        res_update = api_client.patch(
            "/api/v1/admin/legal/terms/",
            {
                "title": "Términos y Condiciones (Actualizados 2026)",
                "content": "# Nuevos términos con cláusulas actualizadas.",
            },
            format="json",
        )
        assert res_update.status_code == status.HTTP_200_OK
        doc = LegalDocument.objects.get(slug="terms")
        assert "Actualizados 2026" in doc.title

    def test_data_portability_export_endpoint(self, api_client, regular_user):
        """3. Portabilidad de datos conforme a RGPD (exportación completa en JSON)."""
        book = Book.objects.create(title="El Quijote", isbn="9788424116286")
        UserBook.objects.create(user=regular_user, book=book, status="completed", current_page=800)
        Review.objects.create(user=regular_user, book=book, rating=5, text="Excelente clásico.")

        refresh = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        res_export = api_client.get("/api/v1/users/account/export/")
        assert res_export.status_code == status.HTTP_200_OK

        # Analizar payload exportado
        data = json.loads(res_export.content.decode("utf-8"))
        assert "profile" in data
        assert data["profile"]["username"] == regular_user.username
        assert "library" in data
        assert len(data["library"]) == 1
        assert data["library"][0]["book_title"] == "El Quijote"
        assert "reviews" in data
        assert len(data["reviews"]) == 1
        assert data["reviews"][0]["rating"] == 5

    def test_account_deletion_and_anonymization_gdpr(self, api_client, regular_user):
        """4. Cancelación y derecho al olvido: eliminación y anonimización irreversible."""
        user_id = regular_user.id
        refresh = RefreshToken.for_user(regular_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # a) Error si la contraseña actual es errónea
        res_err_pass = api_client.post(
            "/api/v1/users/account/delete/",
            {"password": "WrongPassword!", "confirmation": "ELIMINAR"},
            format="json",
        )
        assert res_err_pass.status_code == status.HTTP_400_BAD_REQUEST

        # b) Error si la confirmación no es 'ELIMINAR' o 'DELETE'
        res_err_conf = api_client.post(
            "/api/v1/users/account/delete/",
            {"password": "ValidPassword123!", "confirmation": "NO_SEGURO"},
            format="json",
        )
        assert res_err_conf.status_code == status.HTTP_400_BAD_REQUEST

        # c) Confirmación exitosa de baja
        res_ok = api_client.post(
            "/api/v1/users/account/delete/",
            {"password": "ValidPassword123!", "confirmation": "ELIMINAR"},
            format="json",
        )
        assert res_ok.status_code == status.HTTP_200_OK
        assert res_ok.json()["deleted"] is True

        # Verificar anonimización en base de datos
        regular_user.refresh_from_db()
        assert regular_user.is_active is False
        assert regular_user.deleted_at is not None
        assert regular_user.username == f"deleted_user_{user_id}"
        assert not regular_user.has_usable_password()

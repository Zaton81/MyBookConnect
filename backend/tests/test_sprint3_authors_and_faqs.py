import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from books.models import Author, AuthorClaim, AuthorClaimStatus, Book, Category, FAQ, Review, UserBook
from users.models import Notification

from django.core.cache import cache

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def test_data(db):
    author = Author.objects.create(
        name="Gabriel García Márquez",
        nationality="Colombiana",
        biography="Premio Nobel de Literatura 1982.",
        photo="https://example.com/gabo.jpg",
        enrichment_attempted=True,
        website="https://www.gabrielgarciamarquez.org",
        wikipedia_url="https://es.wikipedia.org/wiki/Gabriel_Garc%C3%ADa_M%C3%A1rquez",
    )
    cache.set(f"bg_author_books_{author.id}", True, 3600)
    b1 = Book.objects.create(title="Cien años de soledad", author=author, average_rating=4.8)
    b2 = Book.objects.create(title="El amor en los tiempos del cólera", author=author, average_rating=4.6)
    author.books.add(b1, b2)

    reader = User.objects.create_user(
        username="lector_gabo",
        email="lector@example.com",
        password="Password123!",
    )
    author_user = User.objects.create_user(
        username="gabo_oficial",
        email="gabo@fundaciongabo.org",
        password="Password123!",
    )
    admin_user = User.objects.create_superuser(
        username="admin_s3",
        email="admin_s3@example.com",
        password="Password123!",
    )

    # Añadir reseñas y biblioteca
    Review.objects.create(book=b1, user=reader, rating=5, title="Obra maestra", text="Inolvidable")
    UserBook.objects.create(book=b1, user=reader, is_read=True)

    return {
        "author": author,
        "book1": b1,
        "book2": b2,
        "reader": reader,
        "author_user": author_user,
        "admin": admin_user,
    }


# ==============================================================================
# 1. Pruebas de Autor Ampliado y Estadísticas (RoadmapV3 Sección 4.1 y 4.2)
# ==============================================================================
@pytest.mark.django_db
class TestAuthorEnrichedFieldsAndStats:
    def test_author_detail_statistics_and_metadata(self, api_client, test_data):
        author = test_data["author"]
        res = api_client.get(f"/api/v1/books/authors/{author.id}/")
        assert res.status_code == status.HTTP_200_OK

        data = res.json()
        assert data["name"] == "Gabriel García Márquez"
        assert data["nationality"] == "Colombiana"
        assert data["website"] == "https://www.gabrielgarciamarquez.org"
        assert data["is_verified"] is False
        assert data["is_claimed"] is False
        assert data["published_books_count"] == 2
        assert data["total_reviews_count"] == 1
        assert data["total_readers_count"] == 1
        assert data["average_rating"] == 4.8  # (5.0 de la reseña en b1 + 4.6 en b2) / 2

    def test_author_can_claim_flag_for_authenticated_users(self, api_client, test_data):
        author = test_data["author"]
        reader = test_data["reader"]

        # Anónimo -> can_claim es False
        res_anon = api_client.get(f"/api/v1/books/authors/{author.id}/")
        assert res_anon.json()["can_claim"] is False

        # Autenticado -> can_claim es True
        api_client.force_authenticate(user=reader)
        res_auth = api_client.get(f"/api/v1/books/authors/{author.id}/")
        assert res_auth.json()["can_claim"] is True


# ==============================================================================
# 2. Pruebas de Reclamación de Autor (RoadmapV3 Sección 4.4 y 4.8)
# ==============================================================================
@pytest.mark.django_db
class TestAuthorClaimWorkflow:
    def test_user_can_submit_author_claim(self, api_client, test_data):
        author = test_data["author"]
        author_user = test_data["author_user"]

        api_client.force_authenticate(user=author_user)

        # 1. Comprobar estado previo
        res_status_before = api_client.get(f"/api/v1/books/authors/{author.id}/claim-status/")
        assert res_status_before.status_code == status.HTTP_200_OK
        assert res_status_before.json()["has_pending_claim"] is False

        # 2. Enviar solicitud de reclamación
        claim_payload = {
            "proof_description": "Represento a los albaceas oficiales y a la Fundación Gabo con acreditación legal.",
            "contact_email": "contacto@fundaciongabo.org",
            "supporting_link": "https://fundaciongabo.org/es/contacto",
        }
        res_claim = api_client.post(
            f"/api/v1/books/authors/{author.id}/claim/",
            claim_payload,
            format="json",
        )
        assert res_claim.status_code == status.HTTP_201_CREATED
        claim_data = res_claim.json()
        assert claim_data["status"] == "pending"
        assert claim_data["author_id"] == author.id

        # 3. Comprobar estado posterior
        res_status_after = api_client.get(f"/api/v1/books/authors/{author.id}/claim-status/")
        assert res_status_after.json()["has_pending_claim"] is True
        assert res_status_after.json()["claim_status"] == "pending"

    def test_duplicate_pending_claim_is_rejected(self, api_client, test_data):
        author = test_data["author"]
        author_user = test_data["author_user"]

        AuthorClaim.objects.create(
            author=author,
            user=author_user,
            status=AuthorClaimStatus.PENDING,
            proof_description="Primera solicitud",
        )

        api_client.force_authenticate(user=author_user)
        res_dup = api_client.post(
            f"/api/v1/books/authors/{author.id}/claim/",
            {"proof_description": "Segunda solicitud repetida"},
            format="json",
        )
        assert res_dup.status_code == status.HTTP_400_BAD_REQUEST
        assert "pendiente" in str(res_dup.json()).lower()

    def test_admin_can_approve_claim_and_verify_author(self, api_client, test_data):
        author = test_data["author"]
        author_user = test_data["author_user"]
        admin = test_data["admin"]

        claim = AuthorClaim.objects.create(
            author=author,
            user=author_user,
            status=AuthorClaimStatus.PENDING,
            proof_description="Prueba válida de identidad",
        )

        # Admin lista las reclamaciones
        api_client.force_authenticate(user=admin)
        res_list = api_client.get("/api/v1/admin/author-claims/?status=pending")
        assert res_list.status_code == status.HTTP_200_OK
        results = res_list.json()
        items = results if isinstance(results, list) else results.get("results", [])
        assert any(item["id"] == claim.id for item in items)

        # Admin aprueba la reclamación
        res_approve = api_client.post(
            f"/api/v1/admin/author-claims/{claim.id}/resolve/",
            {
                "action": "approve",
                "moderation_notes": "Identidad contrastada positivamente con la editorial.",
            },
            format="json",
        )
        assert res_approve.status_code == status.HTTP_200_OK
        assert res_approve.json()["status"] == "approved"

        # Comprobar que el autor quedó verificado y asignado
        author.refresh_from_db()
        assert author.is_verified is True
        assert author.claimed_by == author_user

        # Comprobar que se notificó al usuario
        assert Notification.objects.filter(recipient=author_user).count() == 1

    def test_admin_can_reject_claim(self, api_client, test_data):
        author = test_data["author"]
        author_user = test_data["author_user"]
        admin = test_data["admin"]

        claim = AuthorClaim.objects.create(
            author=author,
            user=author_user,
            status=AuthorClaimStatus.PENDING,
            proof_description="Prueba insuficiente",
        )

        api_client.force_authenticate(user=admin)
        res_reject = api_client.post(
            f"/api/v1/admin/author-claims/{claim.id}/resolve/",
            {
                "action": "reject",
                "moderation_notes": "No se aportó enlace oficial ni correo corporativo.",
            },
            format="json",
        )
        assert res_reject.status_code == status.HTTP_200_OK
        assert res_reject.json()["status"] == "rejected"

        claim.refresh_from_db()
        assert claim.status == AuthorClaimStatus.REJECTED
        assert author.is_verified is False


# ==============================================================================
# 3. Pruebas de Preguntas Frecuentes (FAQs)
# ==============================================================================
@pytest.mark.django_db
class TestFAQsAPI:
    def test_public_faqs_list_only_published(self, api_client):
        FAQ.objects.create(
            question="¿Cómo funciona el feed?",
            answer="Muestra la actividad de los usuarios que sigues.",
            category=FAQ.Category.COMMUNITY,
            order=1,
            is_published=True,
        )
        FAQ.objects.create(
            question="Pregunta secreta o borrador",
            answer="No visible al público aún.",
            category=FAQ.Category.GENERAL,
            order=2,
            is_published=False,
        )

        res = api_client.get("/api/v1/faqs/")
        assert res.status_code == status.HTTP_200_OK
        results = res.json()
        items = results if isinstance(results, list) else results.get("results", [])

        questions = [item["question"] for item in items]
        assert "¿Cómo funciona el feed?" in questions
        assert "Pregunta secreta o borrador" not in questions

    def test_public_faqs_category_filter(self, api_client):
        FAQ.objects.create(
            question="¿Cómo reclamo mi autoría?",
            answer="Desde tu página de autor.",
            category=FAQ.Category.AUTHORS,
            order=1,
            is_published=True,
        )

        res = api_client.get("/api/v1/faqs/?category=authors")
        assert res.status_code == status.HTTP_200_OK
        results = res.json()
        items = results if isinstance(results, list) else results.get("results", [])
        assert all(item["category"] == "authors" for item in items)

    def test_admin_faqs_crud_operations(self, api_client, test_data):
        admin = test_data["admin"]
        reader = test_data["reader"]

        # 1. No admin -> 403
        api_client.force_authenticate(user=reader)
        res_forbidden = api_client.post("/api/v1/admin/faqs/", {
            "question": "Q1",
            "answer": "A1",
            "category": "general",
        }, format="json")
        assert res_forbidden.status_code == status.HTTP_403_FORBIDDEN

        # 2. Admin crea FAQ
        api_client.force_authenticate(user=admin)
        res_create = api_client.post("/api/v1/admin/faqs/", {
            "question": "¿Dónde edito mi perfil?",
            "answer": "En el menú superior derecho.",
            "category": "account",
            "order": 5,
            "is_published": True,
        }, format="json")
        assert res_create.status_code == status.HTTP_201_CREATED
        faq_id = res_create.json()["id"]

        # 3. Admin actualiza FAQ
        res_patch = api_client.patch(f"/api/v1/admin/faqs/{faq_id}/", {
            "order": 1,
        }, format="json")
        assert res_patch.status_code == status.HTTP_200_OK
        assert res_patch.json()["order"] == 1

        # 4. Admin elimina FAQ
        res_delete = api_client.delete(f"/api/v1/admin/faqs/{faq_id}/")
        assert res_delete.status_code == status.HTTP_204_NO_CONTENT
        assert not FAQ.objects.filter(id=faq_id).exists()

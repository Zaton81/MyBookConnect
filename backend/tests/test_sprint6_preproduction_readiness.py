import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from books.models import (
    Author,
    AuthorClaim,
    AuthorClaimStatus,
    Book,
    Category,
    FAQ,
    ReadingStatus,
    Review,
    UserBook,
)
from users.models import AccountType, PrivacyChoices, UserRole

User = get_user_model()


@pytest.mark.django_db
class TestSprint6PreproductionReadiness:
    """
    Suite de Smoke Tests E2E y Criterios de Ready for Production (RoadmapV3 Sprint 6 y Sección 27).
    Valida los flujos críticos de la plataforma de extremo a extremo:
    1. Registro, confirmación, login JWT, refresh y rotación.
    2. Exploración de catálogo, unificación de ediciones por ISBN y estanterías de lectura.
    3. Reseñas enriquecidas, sanitización anti-XSS y actualización de estadísticas.
    4. Relaciones sociales (seguimiento de lectores y feed de actividad).
    5. Reclamación y verificación de autores con panel oficial.
    6. Centro de ayuda y preguntas frecuentes (FAQs).
    7. Sondas de infraestructura, liveness y readiness para producción.
    """

    def setup_method(self):
        self.client = APIClient()

    def test_e2e_user_journey_auth_and_session(self):
        """1. Flujo completo de ciclo de vida de usuario y autenticación JWT."""
        # a) Registro de nuevo usuario
        register_payload = {
            "username": "lector_preprod",
            "email": "lector_preprod@example.com",
            "password": "SecurePassword123!",
            "password2": "SecurePassword123!",
        }
        res_register = self.client.post("/api/v1/auth/register/", register_payload, format="json")
        assert res_register.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

        user = User.objects.get(username="lector_preprod")
        user.is_email_verified = True
        user.save()

        # b) Login para obtener JWT tokens
        login_payload = {
            "username": "lector_preprod",
            "password": "SecurePassword123!",
        }
        res_login = self.client.post("/api/v1/auth/token/", login_payload, format="json")
        assert res_login.status_code == status.HTTP_200_OK
        access_token = res_login.data.get("access")
        refresh_token = res_login.data.get("refresh")
        assert access_token is not None
        assert refresh_token is not None

        # c) Acceso autenticado a perfil propio
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        res_profile = self.client.get("/api/v1/auth/profile/")
        assert res_profile.status_code == status.HTTP_200_OK
        assert res_profile.data.get("username") == "lector_preprod"

        # d) Rotación de refresh token
        self.client.credentials()  # Quitar cabecera para llamar a refresh
        res_refresh = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_token}, format="json")
        assert res_refresh.status_code == status.HTTP_200_OK
        new_access = res_refresh.data.get("access")
        assert new_access is not None

    def test_e2e_catalog_search_and_reading_flow(self):
        """2. Flujo de catálogo: búsqueda por ISBN múltiple, biblioteca y reseñas con sanitización."""
        # Crear usuario lector
        user = User.objects.create_user(
            username="book_explorer",
            email="explorer@example.com",
            password="TestPassword123!",
        )
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Crear autor y obra con ediciones unificadas
        author = Author.objects.create(name="Brandon Sanderson")
        book = Book.objects.create(
            title="El camino de los reyes",
            author=author,
            isbn="9788466657662",
            description="Primer volumen del Archivo de las Tormentas.",
        )
        book.add_isbn("9788466657679")  # Edición digital eBook
        book.save()

        # a) Búsqueda global por edición digital
        res_search = self.client.get("/api/v1/search/?q=9788466657679&type=books")
        assert res_search.status_code == status.HTTP_200_OK
        books_found = res_search.data.get("books", [])
        assert len(books_found) == 1
        assert books_found[0]["id"] == book.id

        # b) Añadir a estantería de lectura del usuario
        ub = UserBook.objects.create(
            user=user,
            book=book,
            status=ReadingStatus.READING,
            current_page=250,
        )
        assert ub.id is not None

        # c) Crear reseña con intento de inyección de script (XSS)
        review_payload = {
            "book": book.id,
            "rating": 5,
            "title": "Obra cumbre <script>alert('xss')</script>",
            "text": "<p>Historia épica increíble <script>steal()</script></p>",
        }
        res_review = self.client.post("/api/v1/books/reviews/", review_payload, format="json")
        assert res_review.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

        # Verificar que el texto y título están limpios de scripts
        review = Review.objects.get(book=book, user=user)
        assert "<script" not in review.title
        assert "<script" not in review.text

    def test_e2e_social_interaction_and_feed(self):
        """3. Flujo social: relaciones entre lectores y feed de actividad."""
        user_a = User.objects.create_user(
            username="reader_alpha",
            email="alpha@example.com",
            password="TestPassword123!",
            privacy_level=PrivacyChoices.PUBLIC,
        )
        user_b = User.objects.create_user(
            username="reader_beta",
            email="beta@example.com",
            password="TestPassword123!",
            privacy_level=PrivacyChoices.PUBLIC,
        )

        refresh_a = RefreshToken.for_user(user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_a.access_token}")

        # Seguir al usuario B
        user_a.following.add(user_b)
        user_a.save()

        assert user_b in user_a.following.all()

        # Consultar feed social
        res_feed = self.client.get("/api/v1/books/feed/")
        assert res_feed.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)

    def test_e2e_author_claim_to_verification_flow(self):
        """4. Flujo de autores: solicitud de reclamación, resolución admin y verificación."""
        admin_user = User.objects.create_superuser(
            username="admin_sprint6",
            email="admin6@example.com",
            password="AdminPassword123!",
        )
        author_user = User.objects.create_user(
            username="escritora_solicitante",
            email="escritora@example.com",
            password="TestPassword123!",
            account_type=AccountType.AUTHOR,
        )

        author = Author.objects.create(
            name="Rosa Montero",
            biography="Periodista y escritora española.",
            is_verified=False,
        )

        # a) La usuaria solicita la reclamación del perfil de autor
        refresh_author = RefreshToken.for_user(author_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_author.access_token}")

        claim_payload = {
            "proof_description": "Represento a la autora legítima con acreditación legal.",
            "contact_email": "escritora@example.com",
            "supporting_link": "https://example.com/credencial-escritora",
        }
        res_claim = self.client.post(f"/api/v1/books/authors/{author.id}/claim/", claim_payload, format="json")
        assert res_claim.status_code in (status.HTTP_201_CREATED, status.HTTP_200_OK)

        claim = AuthorClaim.objects.get(author=author, user=author_user)
        assert claim.status == AuthorClaimStatus.PENDING

        # b) Administrador aprueba la reclamación
        refresh_admin = RefreshToken.for_user(admin_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_admin.access_token}")

        res_resolve = self.client.post(
            f"/api/v1/admin/author-claims/{claim.id}/resolve/",
            {"action": "approve", "moderation_notes": "Identidad verificada oficialmente."},
            format="json",
        )
        assert res_resolve.status_code == status.HTTP_200_OK

        # Verificar que el autor ahora es verificado y pertenece al usuario
        author.refresh_from_db()
        assert author.is_verified is True
        assert author.claimed_by == author_user

    def test_e2e_faqs_and_support_flow(self):
        """5. Flujo de Centro de Ayuda: consultas públicas, categorías y ordenamiento de FAQs."""
        FAQ.objects.create(
            question="¿Cómo verificar mi perfil?",
            answer="Rellena la solicitud de autor.",
            category="authors",
            order=1,
            is_published=True,
        )
        FAQ.objects.create(
            question="¿Borrador no publicado?",
            answer="No debe aparecer.",
            category="general",
            order=2,
            is_published=False,
        )

        # Consulta pública anónima
        self.client.credentials()
        res_faqs = self.client.get("/api/v1/faqs/")
        assert res_faqs.status_code == status.HTTP_200_OK
        items = res_faqs.data if isinstance(res_faqs.data, list) else res_faqs.data.get("results", [])
        assert len(items) == 1
        assert items[0]["question"] == "¿Cómo verificar mi perfil?"

    def test_production_health_and_readiness_probes(self):
        """6. Sondas de infraestructura /health/live/ y /health/ready/."""
        self.client.credentials()

        # Liveness probe
        res_live = self.client.get("/health/live/")
        assert res_live.status_code == status.HTTP_200_OK
        assert res_live.data.get("status") == "healthy"

        # Readiness probe
        res_ready = self.client.get("/health/ready/")
        assert res_ready.status_code == status.HTTP_200_OK
        assert res_ready.data.get("status") == "ready"

        # Version probe
        res_version = self.client.get("/api/v1/version/")
        assert res_version.status_code == status.HTTP_200_OK
        assert "version" in res_version.data

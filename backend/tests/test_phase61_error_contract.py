"""
Suite de pruebas para la Fase 61: Contrato de errores API.

Verifica:
1. Estructura unificada de error: {"error": {"code": "...", "message": "...", "details": {...}}}
2. Códigos de error estables:
   - AUTH_INVALID (401)
   - PERMISSION_DENIED (403)
   - NOT_FOUND (404)
   - VALIDATION_ERROR (400)
   - REVIEW_ALREADY_EXISTS (409/400)
   - BOOK_DUPLICATE (409/400)
   - USER_BLOCKED (403)
   - RATE_LIMITED (429)
   - METHOD_NOT_ALLOWED (405)
3. Retrocompatibilidad: preservación de claves heredadas (detail, campos de serializer) a nivel raíz.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import exceptions, status
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from books.models import Author, Book, Review
from mybookconnect.exceptions import (
    BookDuplicateError,
    ErrorCode,
    RateLimitedError,
    ReviewAlreadyExistsError,
    UserBlockedError,
    custom_exception_handler,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Vistas de prueba para simular excepciones específicas de dominio
# ---------------------------------------------------------------------------
class DummyReviewDuplicateView(APIView):
    permission_classes = []

    def post(self, request):
        raise ReviewAlreadyExistsError()


class DummyBookDuplicateView(APIView):
    permission_classes = []

    def post(self, request):
        raise BookDuplicateError()


class DummyUserBlockedView(APIView):
    permission_classes = []

    def post(self, request):
        raise UserBlockedError()


class DummyRateLimitedView(APIView):
    permission_classes = []

    def get(self, request):
        raise RateLimitedError()



# ---------------------------------------------------------------------------
# Pruebas Unitarias del Exception Handler Centralizado
# ---------------------------------------------------------------------------
class TestCustomExceptionHandlerUnit:
    def test_auth_invalid_handled_correctly(self):
        exc = exceptions.NotAuthenticated("No estás autenticado.")
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED
        assert resp.data["error"]["code"] == ErrorCode.AUTH_INVALID
        assert "error" in resp.data
        assert "detail" in resp.data

    def test_permission_denied_handled_correctly(self):
        exc = exceptions.PermissionDenied("Permisos insuficientes.")
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["error"]["code"] == ErrorCode.PERMISSION_DENIED
        assert resp.data["error"]["message"] == "Permisos insuficientes."

    def test_user_blocked_detected_from_permission_denied(self):
        exc = exceptions.PermissionDenied("No puedes interactuar debido a un bloqueo mutuo.")
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert resp.data["error"]["code"] == ErrorCode.USER_BLOCKED
        assert "bloqueo" in resp.data["error"]["message"]

    def test_not_found_handled_correctly(self):
        exc = exceptions.NotFound("Libro no encontrado.")
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert resp.data["error"]["code"] == ErrorCode.NOT_FOUND

    def test_validation_error_with_field_dict_and_backwards_compat(self):
        exc = exceptions.ValidationError({"title": ["El título es requerido."], "isbn": ["ISBN inválido."]})
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"]["code"] == ErrorCode.VALIDATION_ERROR
        assert "title" in resp.data["error"]["details"]
        assert "isbn" in resp.data["error"]["details"]
        # Retrocompatibilidad
        assert "title" in resp.data
        assert "isbn" in resp.data
        assert "detail" in resp.data

    def test_throttled_handled_as_rate_limited(self):
        exc = exceptions.Throttled(wait=30)
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert resp.data["error"]["code"] == ErrorCode.RATE_LIMITED
        assert "30 segundos" in resp.data["error"]["message"]

    def test_review_already_exists_exception(self):
        exc = ReviewAlreadyExistsError()
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["error"]["code"] == ErrorCode.REVIEW_ALREADY_EXISTS

    def test_book_duplicate_exception(self):
        exc = BookDuplicateError()
        resp = custom_exception_handler(exc, {})
        assert resp.status_code == status.HTTP_409_CONFLICT
        assert resp.data["error"]["code"] == ErrorCode.BOOK_DUPLICATE

    def test_unhandled_exception_fallback(self):
        exc = RuntimeError("Unexpected DB crash")
        resp = custom_exception_handler(exc, {"view": "TestView"})
        assert resp.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert resp.data["error"]["code"] == ErrorCode.INTERNAL_SERVER_ERROR
        assert "error interno" in resp.data["error"]["message"]


# ---------------------------------------------------------------------------
# Pruebas de Integración con Endpoints Reales de la API
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestApiErrorContractIntegration:
    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="contract_user",
            email="contract@example.com",
            password="StrongPassword123!",
        )

    @pytest.fixture
    def client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    @pytest.fixture
    def book(self):
        author = Author.objects.create(name="Gabriel García Márquez")
        return Book.objects.create(
            title="El coronel no tiene quien le escriba",
            author=author,
            isbn="9780307474729",
        )

    def test_unauthenticated_request_returns_auth_invalid(self):
        anonymous_client = APIClient()
        res = anonymous_client.get("/api/v1/auth/profile/")
        assert res.status_code == 401
        assert "error" in res.data
        assert res.data["error"]["code"] == ErrorCode.AUTH_INVALID
        assert "detail" in res.data

    def test_not_found_resource_returns_not_found_code(self, client):
        res = client.get("/api/v1/books/99999999/")
        assert res.status_code == 404
        assert "error" in res.data
        assert res.data["error"]["code"] == ErrorCode.NOT_FOUND

    def test_validation_error_on_review_creation_returns_validation_error_code(self, client, book):
        # Enviar rating inválido (fuera de rango 1..10) o datos faltantes
        res = client.post("/api/v1/reviews/", {"book_id": book.id, "rating": 99}, format="json")
        assert res.status_code == 400
        assert "error" in res.data
        assert res.data["error"]["code"] == ErrorCode.VALIDATION_ERROR
        assert "detail" in res.data

    def test_permission_denied_on_moderation_admin_view(self, client):
        # Usuario normal no staff accediendo a moderación
        res = client.post("/api/v1/admin/moderation/hide/", {"item_type": "review", "item_id": 1})
        assert res.status_code == 403
        assert "error" in res.data
        assert res.data["error"]["code"] == ErrorCode.PERMISSION_DENIED

    def test_user_blocked_contract_on_review_interaction(self, client, user, book):
        # Crear reseña con otro usuario que bloquea a 'user'
        author_user = User.objects.create_user(
            username="blocking_author",
            email="blocking@example.com",
            password="StrongPassword123!",
        )
        author_user.blocked_users.add(user)

        review = Review.objects.create(
            user=author_user,
            book=book,
            rating=5,
            title="Buena lectura",
            text="Texto de la reseña",
        )

        # Intentar dar like o comentar
        res = client.post(f"/api/v1/reviews/{review.id}/like/")
        assert res.status_code == 403
        assert "error" in res.data
        assert res.data["error"]["code"] == ErrorCode.USER_BLOCKED
        assert "detail" in res.data

    def test_method_not_allowed_contract(self, client):
        # Enviar POST a un endpoint que solo admite GET
        res = client.post("/api/v1/auth/profile/")
        assert res.status_code == 405
        assert "error" in res.data
        assert res.data["error"]["code"] == ErrorCode.METHOD_NOT_ALLOWED

    def test_domain_specific_duplicate_views(self):
        factory = APIRequestFactory()

        # Review already exists
        req = factory.post("/fake/")
        view_rev = DummyReviewDuplicateView.as_view()
        res_rev = view_rev(req)
        assert res_rev.status_code == 409
        assert res_rev.data["error"]["code"] == ErrorCode.REVIEW_ALREADY_EXISTS

        # Book duplicate
        view_book = DummyBookDuplicateView.as_view()
        res_book = view_book(req)
        assert res_book.status_code == 409
        assert res_book.data["error"]["code"] == ErrorCode.BOOK_DUPLICATE

        # User blocked
        view_blocked = DummyUserBlockedView.as_view()
        res_blocked = view_blocked(req)
        assert res_blocked.status_code == 403
        assert res_blocked.data["error"]["code"] == ErrorCode.USER_BLOCKED

        # Rate limited
        req_get = factory.get("/fake/")
        view_rate = DummyRateLimitedView.as_view()
        res_rate = view_rate(req_get)
        assert res_rate.status_code == 429
        assert res_rate.data["error"]["code"] == ErrorCode.RATE_LIMITED

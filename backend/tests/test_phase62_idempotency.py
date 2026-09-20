"""
Suite de pruebas para la Fase 62: Idempotencia en operaciones sensibles/costosas.

Verifica:
1. IdempotencyManager: extracción de clave, hashing de payload determinista, bloqueos atómicos en Redis.
2. Decorador @idempotent:
   - Replay idéntico con cabecera 'Idempotent-Replayed: true'.
   - Rechazo por discrepancia de payload (mismo key, diferente cuerpo -> 400).
   - Prevención de condiciones de carrera (petición concurrente en curso -> 409 Conflict).
   - Clave requerida vs opcional.
3. Integración con endpoints reales:
   - POST /api/v1/users/notifications/ (sin duplicación de notificaciones).
   - POST /api/v1/books/sync/external/ (sincronización externa idempotente).
   - POST /api/v1/books/import/csv/confirm/ (importación de biblioteca idempotente).
"""

import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework.views import APIView

from mybookconnect.idempotency import (
    IdempotencyManager,
    IdempotencyStatus,
    idempotent,
)
from users.models import Notification

User = get_user_model()


# ---------------------------------------------------------------------------
# Vistas de prueba para el decorador @idempotent
# ---------------------------------------------------------------------------
class DummyCounterView(APIView):
    permission_classes = []
    call_count = 0

    @idempotent(required=False)
    def post(self, request):
        DummyCounterView.call_count += 1
        return Response(
            {"count": DummyCounterView.call_count, "echo": request.data.get("value")},
            status=status.HTTP_201_CREATED,
        )


class DummyRequiredKeyView(APIView):
    permission_classes = []

    @idempotent(required=True)
    def post(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Pruebas Unitarias de IdempotencyManager
# ---------------------------------------------------------------------------
class TestIdempotencyManagerUnit:
    def setup_method(self):
        cache.clear()

    def test_extract_key_from_standard_and_custom_headers(self):
        factory = APIRequestFactory()

        # Con Idempotency-Key
        req1 = factory.post("/test/", HTTP_IDEMPOTENCY_KEY="key-123")
        assert IdempotencyManager.extract_key(req1) == "key-123"

        # Con X-Idempotency-Key
        req2 = factory.post("/test/", HTTP_X_IDEMPOTENCY_KEY="key-456")
        assert IdempotencyManager.extract_key(req2) == "key-456"

        # Sin cabecera
        req3 = factory.post("/test/")
        assert IdempotencyManager.extract_key(req3) is None

        # Exceso de longitud (> 128 chars)
        long_key = "x" * 129
        req4 = factory.post("/test/", HTTP_IDEMPOTENCY_KEY=long_key)
        assert IdempotencyManager.extract_key(req4) is None

    def test_compute_payload_hash_consistency(self):
        factory = APIRequestFactory()
        req1 = factory.post("/test/", {"a": 1, "b": 2}, format="json")
        req2 = factory.post("/test/", {"b": 2, "a": 1}, format="json")
        req3 = factory.post("/test/", {"a": 1, "b": 999}, format="json")

        hash1 = IdempotencyManager.compute_payload_hash(req1)
        hash2 = IdempotencyManager.compute_payload_hash(req2)
        hash3 = IdempotencyManager.compute_payload_hash(req3)

        assert hash1 == hash2  # Mismo payload con orden de claves distinto
        assert hash1 != hash3  # Distinto payload

    def test_acquire_and_release_lock(self):
        cache_key = "idemp:test:POST:endpoint:key1"
        assert IdempotencyManager.acquire_lock(cache_key, timeout=10) is True
        # Segundo intento concurrente falla
        assert IdempotencyManager.acquire_lock(cache_key, timeout=10) is False

        IdempotencyManager.release_lock(cache_key)
        # Tras liberar, vuelve a poder adquirirse
        assert IdempotencyManager.acquire_lock(cache_key, timeout=10) is True
        IdempotencyManager.release_lock(cache_key)

    def test_save_and_get_stored_record(self):
        cache_key = "idemp:test:POST:endpoint:key2"
        payload_hash = "abc123hash"
        IdempotencyManager.save_response(
            cache_key=cache_key,
            payload_hash=payload_hash,
            status_code=201,
            response_data={"created": True},
            timeout=300,
        )

        record = IdempotencyManager.get_stored_record(cache_key)
        assert record is not None
        assert record["status"] == IdempotencyStatus.COMPLETED
        assert record["payload_hash"] == payload_hash
        assert record["status_code"] == 201
        assert record["response_data"]["created"] is True


# ---------------------------------------------------------------------------
# Pruebas del Decorador @idempotent
# ---------------------------------------------------------------------------
class TestIdempotentDecorator:
    def setup_method(self):
        cache.clear()
        DummyCounterView.call_count = 0

    def test_request_without_key_executes_normally_when_optional(self):
        factory = APIRequestFactory()
        view = DummyCounterView.as_view()

        req1 = factory.post("/test/", {"value": "first"}, format="json")
        res1 = view(req1)
        assert res1.status_code == 201
        assert res1.data["count"] == 1

        req2 = factory.post("/test/", {"value": "second"}, format="json")
        res2 = view(req2)
        assert res2.status_code == 201
        assert res2.data["count"] == 2  # Se ejecutó de nuevo sin idempotencia

    def test_request_with_key_replays_cached_response(self):
        factory = APIRequestFactory()
        view = DummyCounterView.as_view()
        key = str(uuid.uuid4())

        # Primera petición
        req1 = factory.post("/test/", {"value": "cached_val"}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        res1 = view(req1)
        assert res1.status_code == 201
        assert res1.data["count"] == 1
        assert "Idempotent-Replayed" not in res1
        assert res1["Idempotency-Key"] == key

        # Segunda petición idéntica con la misma clave
        req2 = factory.post("/test/", {"value": "cached_val"}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        res2 = view(req2)
        assert res2.status_code == 201
        assert res2.data["count"] == 1  # El contador NO aumentó
        assert res2.data["echo"] == "cached_val"
        assert res2["Idempotent-Replayed"] == "true"
        assert res2["Idempotency-Key"] == key

    def test_request_with_same_key_but_different_payload_fails_with_400(self):
        factory = APIRequestFactory()
        view = DummyCounterView.as_view()
        key = str(uuid.uuid4())

        # Primera petición
        req1 = factory.post("/test/", {"value": "original"}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        res1 = view(req1)
        assert res1.status_code == 201

        # Reutilizar clave con payload distinto -> 400 Bad Request
        req2 = factory.post("/test/", {"value": "different_payload"}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        res2 = view(req2)
        assert res2.status_code == 400
        assert "diferente" in res2.data["detail"]

    def test_concurrent_in_progress_request_returns_409_conflict(self):
        factory = APIRequestFactory()
        view = DummyCounterView.as_view()
        key = str(uuid.uuid4())

        # Simular que la clave ya está en estado PROCESSING
        cache_key = IdempotencyManager.build_cache_key(None, "POST", "/test/", key)
        req = factory.post("/test/", {"value": "data"}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        payload_hash = IdempotencyManager.compute_payload_hash(req)
        IdempotencyManager.set_processing(cache_key, payload_hash)

        # La petición debe devolver 409 Conflict
        res = view(req)
        assert res.status_code == 409
        assert "en proceso" in res.data["detail"]

    def test_required_key_fails_when_header_missing(self):
        factory = APIRequestFactory()
        view = DummyRequiredKeyView.as_view()

        req_missing = factory.post("/test/", {"val": 1}, format="json")
        res_missing = view(req_missing)
        assert res_missing.status_code == 400
        assert "Se requiere la cabecera Idempotency-Key" in res_missing.data["detail"]

        req_valid = factory.post("/test/", {"val": 1}, format="json", HTTP_IDEMPOTENCY_KEY="req-key-1")
        res_valid = view(req_valid)
        assert res_valid.status_code == 200


# ---------------------------------------------------------------------------
# Pruebas de Integración con Endpoints Reales
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestIdempotencyEndpointsIntegration:
    @pytest.fixture(autouse=True)
    def clean_cache(self):
        cache.clear()
        yield
        cache.clear()

    @pytest.fixture
    def user(self):
        return User.objects.create_user(
            username="idemp_user",
            email="idemp@example.com",
            password="StrongPassword123!",
        )

    @pytest.fixture
    def client(self, user):
        c = APIClient()
        c.force_authenticate(user=user)
        return c

    def test_notifications_creation_idempotency_prevents_duplicates(self, client, user):
        key = str(uuid.uuid4())
        payload = {
            "title": "Alerta de prueba",
            "message": "Mensaje de idempotencia",
            "type": "system",
        }

        # 1. Primera emisión de notificación
        res1 = client.post(
            "/api/v1/users/notifications/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert res1.status_code == 201
        notif_id = res1.data["id"]
        assert Notification.objects.filter(recipient=user).count() == 1

        # 2. Reintento con la misma clave de idempotencia
        res2 = client.post(
            "/api/v1/users/notifications/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert res2.status_code == 201
        assert res2["Idempotent-Replayed"] == "true"
        assert res2.data["id"] == notif_id
        # Garantía crítica: ¡No se duplicó en la base de datos!
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_external_sync_endpoint_idempotency(self, client):
        key = str(uuid.uuid4())
        payload = {"author": "Gabriel García Márquez"}

        with patch("books.services.import_books_by_author", return_value=5) as mock_import:
            # 1. Primera llamada a sincronización
            res1 = client.post(
                "/api/v1/books/sync/external/",
                payload,
                format="json",
                HTTP_IDEMPOTENCY_KEY=key,
            )
            assert res1.status_code == 200
            assert res1.data["synced"] is True
            assert res1.data["count"] == 5
            assert mock_import.call_count == 1

            # 2. Reintento inmediato con misma clave
            res2 = client.post(
                "/api/v1/books/sync/external/",
                payload,
                format="json",
                HTTP_IDEMPOTENCY_KEY=key,
            )
            assert res2.status_code == 200
            assert res2["Idempotent-Replayed"] == "true"
            # Garantía crítica: ¡El servicio externo NO fue consultado una segunda vez!
            assert mock_import.call_count == 1

    def test_csv_import_confirm_endpoint_idempotency(self, client):
        key = str(uuid.uuid4())
        payload = {
            "items": [
                {
                    "title": "Libro Idempotente",
                    "author": "Autor Idempotente",
                    "isbn": "9781234567890",
                    "shelf": "read",
                }
            ],
            "update_existing": True,
        }

        # 1. Primera llamada
        res1 = client.post(
            "/api/v1/books/import/csv/confirm/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert res1.status_code == 200
        assert res1.data["success"] is True
        assert res1.data["imported_books_count"] == 1

        # 2. Reintento con misma clave
        res2 = client.post(
            "/api/v1/books/import/csv/confirm/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        assert res2.status_code == 200
        assert res2["Idempotent-Replayed"] == "true"
        assert res2.data["imported_books_count"] == 1


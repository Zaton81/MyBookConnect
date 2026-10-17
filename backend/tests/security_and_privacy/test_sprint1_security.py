import json
from unittest.mock import patch
import pytest
from channels.testing import WebsocketCommunicator
from rest_framework import status
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from django.core.cache import cache

from messages_app.consumers import ChatConsumer
from messages_app.models import Conversation
from users.models import Notification, NotificationType
from users.notification_service import NotificationService

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def users_fixture(db):
    alice = User.objects.create_user(
        username="alice_s1",
        email="alice_s1@example.com",
        password="Password123!",
    )
    bob = User.objects.create_user(
        username="bob_s1",
        email="bob_s1@example.com",
        password="Password123!",
    )
    admin_user = User.objects.create_superuser(
        username="admin_s1",
        email="admin_s1@example.com",
        password="Password123!",
    )
    return {"alice": alice, "bob": bob, "admin": admin_user}


# ==============================================================================
# 1. Seguridad e Integridad de Notificaciones (RoadmapV3 Sección 1.1)
# ==============================================================================
@pytest.mark.django_db
class TestNotificationSecurityAndIntegrity:
    """
    Verifica que la emisión de notificaciones esté vedada a nivel de API pública
    (POST deshabilitado con 405 Method Not Allowed), previniendo IDOR y falsificación,
    y garantizando que solo el servicio interno NotificationService pueda crearlas.
    """

    def test_notification_endpoint_post_disallowed(self, api_client, users_fixture):
        alice = users_fixture["alice"]
        bob = users_fixture["bob"]
        api_client.force_authenticate(user=alice)

        # Intento de falsificar una notificación vía POST
        res = api_client.post(
            "/api/v1/users/notifications/",
            {
                "recipient_id": bob.id,
                "title": "Notificación Falsa",
                "message": "Intento de inyección",
                "type": "SYSTEM",
            },
            format="json",
        )
        assert res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_notification_list_read_only_for_recipient(self, api_client, users_fixture):
        alice = users_fixture["alice"]
        bob = users_fixture["bob"]

        # Crear notificaciones internas legítimas
        Notification.objects.create(
            recipient=alice,
            actor=bob,
            type=NotificationType.FOLLOW,
            title="Alice follow",
            read=False,
        )
        Notification.objects.create(
            recipient=bob,
            actor=alice,
            type=NotificationType.MESSAGE,
            title="Bob message",
            read=False,
        )

        api_client.force_authenticate(user=alice)
        res = api_client.get("/api/v1/users/notifications/")
        assert res.status_code == status.HTTP_200_OK
        results = res.json()
        items = results if isinstance(results, list) else results.get("results", [])
        assert len(items) == 1
        assert items[0]["title"] == "Alice follow"

    def test_notification_detail_idor_protection(self, api_client, users_fixture):
        alice = users_fixture["alice"]
        bob = users_fixture["bob"]

        notif_alice = Notification.objects.create(
            recipient=alice,
            actor=bob,
            type=NotificationType.SYSTEM,
            title="Alerta confidencial de Alice",
        )

        # Bob intenta consultar la notificación de Alice (IDOR -> 404)
        api_client.force_authenticate(user=bob)
        res_bob_get = api_client.get(f"/api/v1/users/notifications/{notif_alice.id}/")
        assert res_bob_get.status_code == status.HTTP_404_NOT_FOUND

        # Bob intenta eliminar la notificación de Alice (IDOR -> 404)
        res_bob_del = api_client.delete(f"/api/v1/users/notifications/{notif_alice.id}/")
        assert res_bob_del.status_code == status.HTTP_404_NOT_FOUND

        # Alice la consulta exitosamente
        api_client.force_authenticate(user=alice)
        res_alice_get = api_client.get(f"/api/v1/users/notifications/{notif_alice.id}/")
        assert res_alice_get.status_code == status.HTTP_200_OK
        assert res_alice_get.json()["title"] == "Alerta confidencial de Alice"

        # Alice la elimina exitosamente
        res_alice_del = api_client.delete(f"/api/v1/users/notifications/{notif_alice.id}/")
        assert res_alice_del.status_code == status.HTTP_204_NO_CONTENT
        assert not Notification.objects.filter(id=notif_alice.id).exists()

    def test_notification_service_internal_only(self, users_fixture):
        alice = users_fixture["alice"]
        bob = users_fixture["bob"]

        # Emisión válida mediante NotificationService
        notif = NotificationService.send_notification(
            recipient=alice,
            actor=bob,
            notif_type=NotificationType.FOLLOW,
            title="Nuevo seguidor",
            message="Bob ahora te sigue",
        )
        assert notif is not None
        assert notif.recipient == alice
        assert notif.actor == bob

        # No auto-notificación
        notif_self = NotificationService.send_notification(
            recipient=alice,
            actor=alice,
            notif_type=NotificationType.LIKE,
            title="Auto Like",
        )
        assert notif_self is None


# ==============================================================================
# 2. Seguridad de Observabilidad y Permisos (RoadmapV3 Sección 1.2)
# ==============================================================================
@pytest.mark.django_db
class TestObservabilitySecurityAndPermissions:
    """
    Verifica que /api/v1/observability/metrics/ esté restringido a IsAdminUser
    y no exponga secretos, contraseñas ni variables de entorno sensibles.
    """

    def test_observability_metrics_anonymous_401(self, api_client):
        res = api_client.get("/api/v1/observability/metrics/")
        assert res.status_code == status.HTTP_401_UNAUTHORIZED

    def test_observability_metrics_non_admin_403(self, api_client, users_fixture):
        alice = users_fixture["alice"]
        api_client.force_authenticate(user=alice)
        res = api_client.get("/api/v1/observability/metrics/")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_observability_metrics_admin_200_and_no_secrets(self, api_client, users_fixture):
        admin_user = users_fixture["admin"]
        api_client.force_authenticate(user=admin_user)
        res = api_client.get("/api/v1/observability/metrics/")
        assert res.status_code == status.HTTP_200_OK

        data = res.json()
        raw_text = json.dumps(data)

        # Verificar secciones principales
        assert "requests" in data
        assert "product_metrics" in data
        assert "system_alerts" in data

        # Verificar que no contenga credenciales ni tokens
        assert "password" not in raw_text.lower()
        assert "secret_key" not in raw_text.lower()
        assert "access_token" not in raw_text.lower()
        assert "jwt" not in raw_text.lower()


# ==============================================================================
# 3. Robustez y Seguridad en WebSockets (RoadmapV3 Sección 1.3)
# ==============================================================================
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWebSocketRobustnessAndSecurity:
    """
    Verifica la robustez de ChatConsumer: captura de JSONDecodeError,
    rechazo de mensajes masivos (> 64 KB), control de acciones desconocidas y rate limiting.
    """

    @pytest.fixture(autouse=True)
    def clean_cache(self):
        cache.clear()
        yield
        cache.clear()

    async def _setup_consumer(self, user):
        conv = await Conversation.objects.acreate()
        await conv.participants.aadd(user)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{conv.id}/",
        )
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": str(conv.id)}}
        communicator.scope["user"] = user

        connected, _ = await communicator.connect()
        assert connected
        return communicator, conv

    async def test_chat_consumer_malformed_json(self, users_fixture):
        alice = users_fixture["alice"]
        communicator, conv = await self._setup_consumer(alice)

        try:
            # Enviar texto plano no JSON
            await communicator.send_to(text_data="<NOT_A_VALID_JSON>")
            response_raw = await communicator.receive_from()
            response = json.loads(response_raw)

            assert response["event"] == "error"
            assert response["code"] == "malformed_json"
            assert "no se pudo decodificar" in response["detail"]
        finally:
            await communicator.disconnect()

    async def test_chat_consumer_payload_too_large(self, users_fixture):
        alice = users_fixture["alice"]
        communicator, conv = await self._setup_consumer(alice)

        try:
            # Enviar mensaje que excede 64 KB (65536 bytes)
            huge_text = "X" * 70000
            huge_payload = json.dumps({"action": "ping", "data": huge_text})

            await communicator.send_to(text_data=huge_payload)
            response_raw = await communicator.receive_from()
            response = json.loads(response_raw)

            assert response["event"] == "error"
            assert response["code"] == "payload_too_large"
        finally:
            await communicator.disconnect()

    async def test_chat_consumer_unknown_action(self, users_fixture):
        alice = users_fixture["alice"]
        communicator, conv = await self._setup_consumer(alice)

        try:
            # Enviar acción inválida
            await communicator.send_to(text_data=json.dumps({"action": "arbitrary_unsupported_action"}))
            response_raw = await communicator.receive_from()
            response = json.loads(response_raw)

            assert response["event"] == "error"
            assert response["code"] == "unknown_action"
            assert "desconocida o no soportada" in response["detail"]
        finally:
            await communicator.disconnect()

    async def test_chat_consumer_rate_limiting(self, users_fixture):
        alice = users_fixture["alice"]
        communicator, conv = await self._setup_consumer(alice)

        try:
            rate_limited_encountered = False
            # Enviar 15 pings en ráfaga (umbral de rate limit: 10 msg/seg)
            for i in range(15):
                await communicator.send_to(text_data=json.dumps({"action": "ping"}))
                resp_raw = await communicator.receive_from()
                resp = json.loads(resp_raw)
                if resp.get("code") == "rate_limited":
                    rate_limited_encountered = True
                    break

            assert rate_limited_encountered is True
        finally:
            await communicator.disconnect()

    async def test_chat_consumer_ping_pong_healthy(self, users_fixture):
        alice = users_fixture["alice"]
        communicator, conv = await self._setup_consumer(alice)

        try:
            await communicator.send_to(text_data=json.dumps({"action": "ping"}))
            response_raw = await communicator.receive_from()
            response = json.loads(response_raw)

            assert response["event"] == "pong"
            assert "timestamp" in response
        finally:
            await communicator.disconnect()


# ==============================================================================
# 4. Sondas de Salud y Sanitización de Errores (RoadmapV3 Sección 1.4)
# ==============================================================================
@pytest.mark.django_db
class TestHealthProbesSecurity:
    """
    Verifica que /health/live y /health/ready operen desacopladas y que
    la sonda de readiness devuelva 503 ante fallos sin filtrar excepciones internas.
    """

    def test_liveness_probe_isolated(self, api_client):
        res = api_client.get("/health/live/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "healthy"
        assert data["process"] == "alive"

    def test_readiness_probe_healthy(self, api_client):
        res = api_client.get("/health/ready/")
        assert res.status_code == status.HTTP_200_OK
        data = res.json()
        assert data["status"] == "ready"
        assert data["services"]["database"] == "ready"
        assert data["services"]["cache"] == "ready"

    def test_readiness_probe_failure_sanitized(self, api_client):
        # Simular fallo en base de datos
        with patch("django.db.connection.cursor", side_effect=Exception("OperationalError: FATAL password auth failed for user postgres")):
            res = api_client.get("/health/ready/")
            assert res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = res.json()
            assert data["status"] == "not_ready"
            # Asegurar que el mensaje no filtre la contraseña ni el detalle interno de la base de datos
            assert data["services"]["database"] == "unhealthy"
            assert "password" not in json.dumps(data).lower()

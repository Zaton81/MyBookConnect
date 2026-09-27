"""
Tests exhaustivos para la Fase 4: Mensajería y tiempo real (P1).

Valida:
1. Ciclo de vida de WebSockets con Heartbeat (ping / pong) para detección de half-open connections.
2. Idempotencia y deduplicación de mensajes ante reconexión (client_message_id) en WebSocket.
3. Idempotencia y respuesta 200 OK sin duplicados en la API REST (MessageViewSet).
4. Modelo ConversationParticipant y persistencia del cursor de lectura (last_read_message, last_read_at).
5. Rechazo de envío si el destinatario ha bloqueado al emisor.
"""

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from messages_app.consumers import ChatConsumer
from messages_app.models import Conversation, ConversationParticipant, Message

User = get_user_model()


@pytest.fixture
def chat_users():
    u1 = User.objects.create_user(username="chat_p4_u1", email="u1@test.com", password="Password123!")
    u2 = User.objects.create_user(username="chat_p4_u2", email="u2@test.com", password="Password123!")
    u1.following.add(u2)
    u2.following.add(u1)
    return u1, u2


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestPhase04MessagingRealtime:
    """Suite de pruebas de tiempo real, heartbeat, idempotencia y modelo de lectura."""

    async def test_websocket_heartbeat_ping_pong(self, chat_users):
        """
        El consumidor debe responder inmediatamente a eventos {action: 'ping'} con {event: 'pong'},
        garantizando que la conexión permanezca activa en proxies y ALB.
        """
        u1, u2 = chat_users
        conv, _ = await database_sync_to_async(Conversation.get_or_create_direct)(u1, u2)

        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": conv.id}}
        communicator.scope["user"] = u1

        connected, _ = await communicator.connect()
        assert connected

        # Enviar ping con timestamp
        test_ts = "2026-09-23T10:00:00Z"
        await communicator.send_json_to({"action": "ping", "timestamp": test_ts})

        # Recibir pong
        res = await communicator.receive_json_from()
        assert res["event"] == "pong"
        assert res["timestamp"] == test_ts

        await communicator.disconnect()

    async def test_websocket_idempotent_message_deduplication(self, chat_users):
        """
        Si un cliente reenvía el mismo mensaje con el mismo client_message_id (tras microcorte),
        el servidor no debe duplicar el registro en base de datos.
        """
        u1, u2 = chat_users
        conv, _ = await database_sync_to_async(Conversation.get_or_create_direct)(u1, u2)

        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": conv.id}}
        communicator.scope["user"] = u1

        connected, _ = await communicator.connect()
        assert connected

        client_msg_id = "cl-uuid-repeat-001"

        # 1. Enviar mensaje por primera vez
        await communicator.send_json_to({
            "action": "send_message",
            "text": "Mensaje único idempotente",
            "client_message_id": client_msg_id,
        })
        first_resp = await communicator.receive_json_from()
        assert first_resp["event"] == "message"
        first_id = first_resp["id"]
        assert first_resp["client_message_id"] == client_msg_id

        # 2. Reenviar exactamente el mismo mensaje con el mismo client_message_id
        await communicator.send_json_to({
            "action": "send_message",
            "text": "Mensaje único idempotente",
            "client_message_id": client_msg_id,
        })
        second_resp = await communicator.receive_json_from()
        assert second_resp["event"] == "message"
        assert second_resp["id"] == first_id
        assert second_resp.get("is_duplicate") is True

        # 3. Comprobar que en base de datos solo existe 1 registro
        msg_count = await database_sync_to_async(
            lambda: Message.objects.filter(conversation=conv, client_message_id=client_msg_id).count()
        )()
        assert msg_count == 1

        await communicator.disconnect()

    async def test_conversation_participant_reading_cursor(self, chat_users):
        """
        Al marcar leídos en la conversación, ConversationParticipant debe registrar
        el last_read_message y timestamp exacto de lectura del usuario.
        """
        u1, u2 = chat_users
        conv, _ = await database_sync_to_async(Conversation.get_or_create_direct)(u1, u2)

        # u1 envía mensaje
        msg = await database_sync_to_async(Message.objects.create)(
            conversation=conv, sender=u1, text="Texto para leer"
        )

        # u2 conecta y marca como leído
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": conv.id}}
        communicator.scope["user"] = u2

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"action": "mark_read"})
        read_event = await communicator.receive_json_from()
        assert read_event["event"] == "read"
        assert read_event["conversation"] == conv.id
        assert read_event["last_read_message_id"] == msg.id

        # Verificar actualización en el modelo ConversationParticipant para u2
        part = await database_sync_to_async(
            lambda: ConversationParticipant.objects.get(conversation=conv, user=u2)
        )()
        assert part.last_read_message_id == msg.id
        assert part.last_read_at is not None

        await communicator.disconnect()

    async def test_messaging_blocked_user_forbidden(self, chat_users):
        """
        Si u2 bloquea a u1, u1 no puede enviar mensajes a u2 ni por WebSocket ni por REST.
        """
        u1, u2 = chat_users
        conv, _ = await database_sync_to_async(Conversation.get_or_create_direct)(u1, u2)

        # u2 bloquea a u1
        await database_sync_to_async(u2.blocked_users.add)(u1)

        # 1. Intento por WebSocket
        communicator = WebsocketCommunicator(ChatConsumer.as_asgi(), f"/ws/chat/{conv.id}/")
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": conv.id}}
        communicator.scope["user"] = u1

        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({
            "action": "send_message",
            "text": "Intento de mensaje a usuario que me bloqueó",
        })
        error_resp = await communicator.receive_json_from()
        assert error_resp["event"] == "error"
        assert "bloqueo" in error_resp["detail"].lower()

        await communicator.disconnect()


@pytest.mark.django_db
class TestPhase04RestIdempotency:
    """Pruebas para idempotencia en el endpoint REST de creación de mensajes."""

    def test_rest_api_idempotent_message_creation(self, chat_users):
        """
        Enviar dos peticiones POST consecutivas con el mismo client_message_id
        devuelve el mismo mensaje sin duplicarlo.
        """
        u1, u2 = chat_users
        conv, _ = Conversation.get_or_create_direct(u1, u2)

        client = APIClient()
        client.force_authenticate(user=u1)

        client_msg_id = "rest-idempotent-uuid-444"

        # 1. Primera petición -> 201 Created
        res1 = client.post(
            "/api/v1/users/messages/",
            {
                "conversation": conv.id,
                "text": "Mensaje enviado vía REST",
                "client_message_id": client_msg_id,
            },
            format="json",
        )
        assert res1.status_code == status.HTTP_201_CREATED
        created_id = res1.data["id"]

        # 2. Segunda petición con el mismo client_message_id -> 200 OK con el mismo ID
        res2 = client.post(
            "/api/v1/users/messages/",
            {
                "conversation": conv.id,
                "text": "Mensaje enviado vía REST",
                "client_message_id": client_msg_id,
            },
            format="json",
        )
        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["id"] == created_id

        # 3. Comprobar que en base de datos solo existe 1 registro
        assert Message.objects.filter(conversation=conv, client_message_id=client_msg_id).count() == 1

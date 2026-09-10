import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from messages_app.consumers import ChatConsumer
from messages_app.models import Conversation, Message
from users.models import Notification, NotificationType

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def chat_users():
    user1 = User.objects.create_user(username='chat_user1', email='chat1@example.com', password='password123')
    user2 = User.objects.create_user(username='chat_user2', email='chat2@example.com', password='password123')
    user3 = User.objects.create_user(username='chat_user3', email='chat3@example.com', password='password123')
    return {'u1': user1, 'u2': user2, 'u3': user3}


@pytest.mark.django_db
class TestCanonicalConversationAndMutations:
    def test_canonical_one_on_one_conversation(self, chat_users):
        u1, u2 = chat_users['u1'], chat_users['u2']

        conv1, created1 = Conversation.get_or_create_direct(u1, u2)
        assert created1 is True
        assert set(conv1.participants.all()) == {u1, u2}

        # B -> A must return the exact same conversation
        conv2, created2 = Conversation.get_or_create_direct(u2, u1)
        assert created2 is False
        assert conv1.id == conv2.id
        assert Conversation.objects.filter(participants=u1).filter(participants=u2).count() == 1

    def test_read_only_viewsets_forbid_mutation(self, api_client, chat_users):
        u1, u2 = chat_users['u1'], chat_users['u2']
        conv, _ = Conversation.get_or_create_direct(u1, u2)
        msg = Message.objects.create(conversation=conv, sender=u1, text='Original Message')

        api_client.force_authenticate(user=u1)

        # 1. DELETE /conversations/<id>/ -> 405 Method Not Allowed
        del_conv = api_client.delete(f'/api/v1/users/conversations/{conv.id}/')
        assert del_conv.status_code == 405

        # 2. PUT /conversations/<id>/ -> 405 Method Not Allowed
        put_conv = api_client.put(f'/api/v1/users/conversations/{conv.id}/', {})
        assert put_conv.status_code == 405

        # 3. DELETE /messages/<id>/ -> 405 Method Not Allowed
        del_msg = api_client.delete(f'/api/v1/users/messages/{msg.id}/')
        assert del_msg.status_code == 405

        # 4. PUT /messages/<id>/ -> 405 Method Not Allowed
        put_msg = api_client.put(f'/api/v1/users/messages/{msg.id}/', {'text': 'Altered Message'})
        assert put_msg.status_code == 405

    def test_access_conversation_unauthorized_denied(self, api_client, chat_users):
        u1, u2, u3 = chat_users['u1'], chat_users['u2'], chat_users['u3']
        conv, _ = Conversation.get_or_create_direct(u1, u2)
        Message.objects.create(conversation=conv, sender=u1, text='Secret between 1 and 2')

        # u3 is not a participant
        api_client.force_authenticate(user=u3)
        res = api_client.get(f'/api/v1/users/messages/?conversation={conv.id}')
        assert res.status_code == 200
        # Results should be empty because u3 has no access
        items = res.data if isinstance(res.data, list) else res.data.get('results', [])
        assert len(items) == 0


@pytest.mark.django_db
class TestNotificationSystem:
    def test_notifications_created_on_follow_and_message(self, api_client, chat_users):
        u1, u2 = chat_users['u1'], chat_users['u2']

        # 1. Follow creates notification
        api_client.force_authenticate(user=u1)
        follow_res = api_client.post(f'/api/v1/users/{u2.id}/follow/')
        assert follow_res.status_code == 200

        notif_follow = Notification.objects.filter(recipient=u2, actor=u1, type=NotificationType.FOLLOW).first()
        assert notif_follow is not None
        assert notif_follow.read is False

        # 2. Message creates notification
        conv, _ = Conversation.get_or_create_direct(u1, u2)
        msg_res = api_client.post('/api/v1/users/messages/', {
            'conversation': conv.id,
            'text': 'Hola desde la prueba de notificaciones'
        })
        assert msg_res.status_code == 201

        notif_msg = Notification.objects.filter(recipient=u2, actor=u1, type=NotificationType.MESSAGE).first()
        assert notif_msg is not None
        assert 'Hola desde la prueba' in notif_msg.message

        # 3. Check endpoints from u2 perspective
        api_client.force_authenticate(user=u2)
        count_res = api_client.get('/api/v1/users/notifications/unread-count/')
        assert count_res.status_code == 200
        assert count_res.data['unread_count'] == 2

        list_res = api_client.get('/api/v1/users/notifications/')
        assert list_res.status_code == 200
        notifs = list_res.data if isinstance(list_res.data, list) else list_res.data.get('results', [])
        assert len(notifs) >= 2

        # 4. Mark single as read
        read_res = api_client.post(f'/api/v1/users/notifications/{notif_follow.id}/read/')
        assert read_res.status_code == 200
        notif_follow.refresh_from_db()
        assert notif_follow.read is True

        # 5. Mark all as read
        read_all_res = api_client.post('/api/v1/users/notifications/read-all/')
        assert read_all_res.status_code == 200
        assert Notification.objects.filter(recipient=u2, read=False).count() == 0


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestWebSocketChatConsumer:
    async def test_websocket_unauthenticated_rejected(self):
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            "/ws/chat/1/",
        )
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": 1}}
        communicator.scope["user"] = None

        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == 4001

    async def test_websocket_non_participant_rejected(self, chat_users):
        from channels.db import database_sync_to_async

        u1, u2, u3 = chat_users['u1'], chat_users['u2'], chat_users['u3']
        conv, _ = await database_sync_to_async(Conversation.get_or_create_direct)(u1, u2)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{conv.id}/",
        )
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": conv.id}}
        communicator.scope["user"] = u3  # u3 not a participant

        connected, close_code = await communicator.connect()
        assert not connected
        assert close_code == 4003

    async def test_websocket_authenticated_messaging(self, chat_users):
        from channels.db import database_sync_to_async

        u1, u2 = chat_users['u1'], chat_users['u2']
        await database_sync_to_async(u1.following.add)(u2)
        conv, _ = await database_sync_to_async(Conversation.get_or_create_direct)(u1, u2)

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{conv.id}/",
        )
        communicator.scope["url_route"] = {"kwargs": {"conversation_id": conv.id}}
        communicator.scope["user"] = u1

        connected, _ = await communicator.connect()
        assert connected

        # Enviar mensaje
        await communicator.send_json_to({
            "action": "send_message",
            "text": "Mensaje en tiempo real vía WebSocket",
        })

        # Recibir broadcast
        response = await communicator.receive_json_from()
        assert response["event"] == "message"
        assert response["text"] == "Mensaje en tiempo real vía WebSocket"
        assert response["sender"] == u1.id

        await communicator.disconnect()

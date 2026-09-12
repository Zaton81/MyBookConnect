import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from .models import Conversation, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        self.group_name = f"chat_conv_{self.conversation_id}"
        user = self.scope.get("user")
        # Validar participante
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        can_access = await self._can_access(user.id, self.conversation_id)
        if not can_access:
            await self.close(code=4003)
            return
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        payload = json.loads(text_data)
        action = payload.get("action")
        user = self.scope.get("user")
        if action == "send_message":
            text = payload.get("text", "").strip()
            if not text:
                return
            can_send = await self._can_send_message(user.id, self.conversation_id)
            if not can_send:
                await self.send(text_data=json.dumps({
                    "event": "error",
                    "detail": "No puedes enviar mensajes a esta conversación debido a una restricción de privacidad o bloqueo.",
                }))
                return

            msg = await self._create_message(self.conversation_id, user.id, text)
            event = {
                "type": "chat.message",
                "message": {
                    "id": msg["id"],
                    "conversation": int(self.conversation_id),
                    "sender": user.id,
                    "text": msg["text"],
                    "image": None,
                    "created_at": msg["created_at"],
                    "read": False,
                },
            }
            await self.channel_layer.group_send(self.group_name, event)
        elif action == "mark_read":
            await self._mark_read(self.conversation_id, user.id)
            await self.channel_layer.group_send(self.group_name, {
                "type": "chat.read",
                "conversation": int(self.conversation_id),
            })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({"event": "message", **event["message"]}))

    async def chat_read(self, event):
        await self.send(text_data=json.dumps({"event": "read", "conversation": event["conversation"]}))

    @database_sync_to_async
    def _can_access(self, user_id: int, conversation_id: int) -> bool:
        from users.policies import can_access_conversation

        conv = Conversation.objects.filter(id=conversation_id).first()
        user = User.objects.filter(id=user_id).first()
        return bool(conv and user and can_access_conversation(user, conv))

    @database_sync_to_async
    def _can_send_message(self, sender_id: int, conversation_id: int) -> bool:
        from users.policies import can_access_conversation, can_message

        conv = Conversation.objects.filter(id=conversation_id).first()
        user = User.objects.filter(id=sender_id).first()
        if not conv or not user or not can_access_conversation(user, conv):
            return False
        for participant in conv.participants.exclude(id=sender_id):
            if not can_message(user, participant):
                return False
        return True

    @database_sync_to_async
    def _create_message(self, conversation_id: int, sender_id: int, text: str):
        from users.models import Notification, NotificationType

        conv = Conversation.objects.get(id=conversation_id)
        user = User.objects.get(id=sender_id)
        msg = Message.objects.create(conversation=conv, sender=user, text=text)

        # Generar notificación para los demás participantes
        for participant in conv.participants.exclude(id=sender_id):
            Notification.objects.create(
                recipient=participant,
                actor=user,
                type=NotificationType.MESSAGE,
                title=f'Mensaje de {user.username}',
                message=text[:80],
                link=f'/chat?conversationId={conv.id}',
            )

        return {
            "id": msg.id,
            "text": msg.text,
            "created_at": msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def _mark_read(self, conversation_id: int, user_id: int):
        Message.objects.filter(conversation_id=conversation_id).exclude(sender_id=user_id).update(read=True)

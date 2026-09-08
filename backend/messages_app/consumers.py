import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
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
        is_participant = await self._is_participant(user.id, self.conversation_id)
        if not is_participant:
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
    def _is_participant(self, user_id: int, conversation_id: int) -> bool:
        conv = Conversation.objects.filter(id=conversation_id, participants__id=user_id).exists()
        return bool(conv)

    @database_sync_to_async
    def _create_message(self, conversation_id: int, sender_id: int, text: str):
        conv = Conversation.objects.get(id=conversation_id)
        user = User.objects.get(id=sender_id)
        msg = Message.objects.create(conversation=conv, sender=user, text=text)
        return {
            "id": msg.id,
            "text": msg.text,
            "created_at": msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def _mark_read(self, conversation_id: int, user_id: int):
        Message.objects.filter(conversation_id=conversation_id).exclude(sender_id=user_id).update(read=True)

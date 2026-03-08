"""
WebSocket consumer for real-time messages.
Clients join group messages_user_{user_id}; server sends message.new events to receiver's group.
"""
import json
from django.contrib.auth.models import AnonymousUser
from channels.generic.websocket import AsyncWebsocketConsumer


def messages_group(user_id):
    return f"messages_user_{user_id}"


def session_group(user_id):
    return f"session_user_{user_id}"


class MessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4401)
            return
        self.group_name = messages_group(self.user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def message_new(self, event):
        """Send the new message payload to the WebSocket (called by channel_layer.group_send)."""
        message_data = event.get("message")
        if message_data is not None:
            await self.send(text_data=json.dumps({"type": "message.new", "message": message_data}, default=str))


class SessionConsumer(AsyncWebsocketConsumer):
    """WebSocket for session revoke: when user logs in elsewhere, server broadcasts session.revoked."""

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4401)
            return
        self.group_name = session_group(self.user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def session_revoked(self, event):
        """Forward session.revoked to client (current_token = new valid token; others should logout)."""
        current_token = event.get("current_token", "")
        await self.send(text_data=json.dumps({"type": "session.revoked", "current_token": current_token}))

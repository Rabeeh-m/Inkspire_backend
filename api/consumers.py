
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
import json
from channels.db import database_sync_to_async
from api.models import User, Message


class PersonalChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_id = data['sender_id']
        room_id = data['room_id']
        file_url = data.get('file_url') 

        # Save message to the database
        await self.save_message(room_id, sender_id, message, file_url)

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender_id": sender_id,
                "file_url": file_url, 
            }
        )

    async def chat_message(self, event):
        message = event["message"]
        sender_id = event["sender_id"]
        file_url = event.get("file_url")  # Add file URL

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "message": message,
            "sender_id": sender_id,
            "file_url": file_url, 
        }))

    @database_sync_to_async
    def save_message(self, room_id, sender_id, text, file_url):
        Message.objects.create(room_id=room_id, sender_id=sender_id, text=text, file=file_url)
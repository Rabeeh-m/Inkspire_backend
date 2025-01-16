# from channels.generic.websocket import AsyncWebsocketConsumer
# import json


# class PersonalChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         request_user = self.scope['user']
#         print(request_user,"<-------->USER")
#         # if request_user.is_authenticated:
#         chat_with_user = self.scope['url_route']['kwargs']['id']
#         user_ids = [int(request_user.id), int(chat_with_user)]
#         user_ids = sorted(user_ids)
#         self.room_group_name = f"chat_{user_ids[0]}-{user_ids[1]}"
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )
#         await self.accept()
    
#     async def receive(self, text_data=None, bytes_data=None):
#         data = json.loads(text_data)
#         message = data['message']
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 "type": "chat_message",
#                 "message": message
#             }
#         )
               
#     async def disconnect(self, code):
#         self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )
        
#     async def chat_message(self, event):
#         message = event["message"]
#         await self.send(text_data=json.dumps({
#             "message": message
#         }))


from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
import json
from channels.db import database_sync_to_async
from api.models import User


class PersonalChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        
        access_token = self.scope['query_string'].decode().split('=')[-1]

        if not access_token:
            print("No access token found in cookies.")
            await self.close()
            return

        # Validate the JWT token
        try:
            decoded_data = jwt_decode(access_token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = decoded_data.get('user_id')
            request_user = await self.get_user(user_id)
            
            if not request_user:
                await self.close()
                return

            # Attach the authenticated user to the scope
            self.scope['user'] = request_user
        except (InvalidToken, TokenError) as e:
            print("Invalid token:", e)
            await self.close()
            return

        # Proceed with room setup
        chat_with_user = self.scope['url_route']['kwargs'].get('id')
        try:
            user_ids = [int(request_user.id), int(chat_with_user)]
            user_ids = sorted(user_ids)
            self.room_group_name = f"chat_{user_ids[0]}-{user_ids[1]}"
        except (TypeError, ValueError) as e:
            print("Error parsing user IDs:", e)
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
    
    @database_sync_to_async
    def get_user(self, user_id):
        # This method will now run in a separate thread to prevent blocking the event loop.
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        message = data.get('message')
        if message:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message
                }
            )

    async def disconnect(self, code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def chat_message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({
            "message": message
        }))

    

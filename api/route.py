from django.urls import path
from .consumers import PersonalChatConsumer

websocket_urlpatterns = [
    path('ws/chat/<str:room_name>/', PersonalChatConsumer.as_asgi()),
]
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

import json

from chat.models import MessageSupport, ChatSupport, Message, Chat

User = get_user_model()


class BaseChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        try:
            token = self.scope['query_string'].decode().split('=')[1]
            UntypedToken(token)
        except (IndexError, InvalidToken, TokenError):
            await self.close()
            return

        self.scope['user'] = await self.get_user_from_token(token)

        if not await self.user_has_access():
            await self.close()
            return

        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )

        await self.accept()
        await self.send_previous_messages()

    @database_sync_to_async
    def get_user_from_token(self, token):
        validated_token = JWTAuthentication().get_validated_token(token)
        return JWTAuthentication().get_user(validated_token)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json.get('message')
        file = text_data_json.get('file')
        user = self.scope['user']

        message = await self.save_message(user, message_content, file)

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': self.format_message(message, user)
            }
        )

    @database_sync_to_async
    def save_message(self, user, message_content, file):
        chat = self.get_chat_instance()
        return self.create_message_instance(chat, user, message_content, file)

    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))

    @database_sync_to_async
    def user_has_access(self):
        user = self.scope['user']
        if user.is_anonymous:
            return False

        try:
            chat = self.get_chat_instance()
        except self.get_chat_model().DoesNotExist:
            return False

        return self.check_user_access(user, chat)

    @database_sync_to_async
    def get_previous_messages(self):
        chat = self.get_chat_instance()
        messages = self.get_messages_queryset(chat)
        return [self.format_message(message, message.sender) for message in messages]

    async def send_previous_messages(self):
        previous_messages = await self.get_previous_messages()
        await self.send(text_data=json.dumps({
            'type': 'previous_messages',
            'messages': previous_messages
        }))

    def format_message(self, message, user):
        message_data = {
            'id': message.id,
            'sender': {
                'id': user.id,
                'first_name': user.first_name,
                'avatar': user.avatar.url if user.avatar else None,
            },
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
        }

        if message.file:
            message_data['file'] = message.file.url

        return message_data

    def get_chat_instance(self):
        raise NotImplementedError

    def get_chat_model(self):
        raise NotImplementedError

    def create_message_instance(self, chat, user, message_content, file):
        raise NotImplementedError

    def get_messages_queryset(self, chat):
        raise NotImplementedError

    def check_user_access(self, user, chat):
        raise NotImplementedError


class ChatConsumer(BaseChatConsumer):
    def get_chat_instance(self):
        return Chat.objects.select_related('trip', 'trip__organizer', 'trip__vehicle__owner').get(id=self.chat_id)

    def get_chat_model(self):
        return Chat

    def create_message_instance(self, chat, user, message_content, file):
        return Message.objects.create(chat=chat, sender=user, content=message_content, file=file)

    def get_messages_queryset(self, chat):
        return chat.messages.order_by('timestamp').select_related('sender').all()

    def check_user_access(self, user, chat):
        if user.role == 'admin':
            return True
        return user in chat.participants.all() or user == chat.trip.organizer or user == chat.trip.vehicle.owner


class ChatSupportConsumer(BaseChatConsumer):
    def get_chat_instance(self):
        return self.get_chat_model().objects.select_related('creator', 'topic').get(id=self.chat_id)

    def get_chat_model(self):
        return ChatSupport

    def create_message_instance(self, chat, user, message_content, file):
        return MessageSupport.objects.create(support_chat=chat, sender=user, content=message_content, file=file)

    def get_messages_queryset(self, chat):
        return chat.message_support.select_related('sender').order_by('timestamp').all()

    def check_user_access(self, user, chat):
        if user.role == 'admin':
            return True
        return user in chat.participants.all()

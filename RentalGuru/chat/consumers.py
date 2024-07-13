from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

import json

from .models import Chat, Message, ChatSupport, MessageSupport

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        token = self.scope['query_string'].decode().split('=')[1]

        try:
            UntypedToken(token)
        except (InvalidToken, TokenError) as e:
            await self.close()
            return

        user = await self.get_user_from_token(token)
        self.scope['user'] = user

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
        from rest_framework_simplejwt.authentication import JWTAuthentication
        validated_token = JWTAuthentication().get_validated_token(token)
        return JWTAuthentication().get_user(validated_token)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_content = text_data_json['message']
        user = self.scope['user']

        message = await self.save_message(user, message_content)

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'sender': {
                        'id': user.id,
                        'first_name': user.first_name,
                        'avatar': user.avatar.url if user.avatar else None,
                    },
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                }
            }
        )

    @database_sync_to_async
    def save_message(self, user, message_content):
        chat = Chat.objects.get(id=self.chat_id)
        return Message.objects.create(
            chat=chat,
            sender=user,
            content=message_content
        )

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
            chat = Chat.objects.get(id=self.chat_id)
        except Chat.DoesNotExist:
            return False

        if user.role == 'admin':
            return True

        return user in chat.participants.all() or user == chat.trip.organizer or user == chat.trip.vehicle.owner

    @database_sync_to_async
    def get_previous_messages(self):
        chat = Chat.objects.get(id=self.chat_id)
        messages = chat.messages.order_by('timestamp').all()
        return [
            {
                'id': message.id,
                'sender': {
                    'id': message.sender.id,
                    'first_name': message.sender.first_name,
                    'avatar': message.sender.avatar.url if message.sender.avatar else None,
                },
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
            }
            for message in messages
        ]

    async def send_previous_messages(self):
        previous_messages = await self.get_previous_messages()
        await self.send(text_data=json.dumps({
            'type': 'previous_messages',
            'messages': previous_messages
        }))

# Чат с техподдержкой


class ChatSupportConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        try:
            token = self.scope['query_string'].decode().split('=')[1]
        except IndexError:
            await self.close()
            return

        try:
            UntypedToken(token)
        except (InvalidToken, TokenError) as e:
            await self.close()
            return

        user = await self.get_user_from_token(token)
        self.scope['user'] = user

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
        message_content = text_data_json['message']
        user = self.scope['user']

        message = await self.save_message(user, message_content)

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'sender': {
                        'id': user.id,
                        'username': user.username,
                        'avatar': user.avatar.url if user.avatar else None,
                    },
                    'content': message.content,
                    'timestamp': message.timestamp.isoformat(),
                }
            }
        )

    @database_sync_to_async
    def save_message(self, user, message_content):
        chat = ChatSupport.objects.get(id=self.chat_id)
        return MessageSupport.objects.create(
            support_chat=chat,
            sender=user,
            content=message_content
        )

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
            chat = ChatSupport.objects.get(id=self.chat_id)
        except ChatSupport.DoesNotExist:
            return False

        if user.role == 'admin':
            return True

        return user in chat.participants.all()

    @database_sync_to_async
    def get_previous_messages(self):
        chat = ChatSupport.objects.get(id=self.chat_id)
        messages = chat.message_support.order_by('timestamp').all()
        return [
            {
                'id': message.id,
                'sender': {
                    'id': message.sender.id,
                    'username': message.sender.username,
                    'avatar': message.sender.avatar.url if message.sender.avatar else None,
                },
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
            }
            for message in messages
        ]

    async def send_previous_messages(self):
        previous_messages = await self.get_previous_messages()
        await self.send(text_data=json.dumps({
            'type': 'previous_messages',
            'messages': previous_messages
        }))

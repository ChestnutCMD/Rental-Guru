from django.utils import timezone
from googletrans import Translator
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import json
from chat.models import MessageSupport, ChatSupport, Message, Chat
from .tasks import translate_message

translator = Translator()


class BaseChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        query_params = dict(x.split('=') for x in self.scope['query_string'].decode().split('&'))
        token = query_params.get('token')
        self.language = query_params.get('lang', 'en')  # Default to English if no language is specified

        try:
            UntypedToken(token)
        except (InvalidToken, TokenError):
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

        # Log message content before translation
        print(f"Original message: {message_content}")

        # Translate message content
        try:
            translated_message_content = translator.translate(message_content, dest=self.language).text
        except Exception as e:
            print(f"Error during translation: {e}")
            translated_message_content = message_content

        # Log translated message content
        print(f"Translated message: {translated_message_content}")

        message = await self.save_message(user, translated_message_content, file)

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
        user = self.scope['user']

        show_all_messages = (
                user.role in ['admin', 'manager'] or
                (hasattr(chat.trip.vehicle, 'owner') and
                 chat.trip.vehicle.owner.lessor.franchise and
                 chat.trip.vehicle.owner.lessor.franchise.director == user)
        )

        if show_all_messages:
            messages = self.get_messages_queryset(chat)
        else:
            messages = self.get_messages_queryset(chat).filter(deleted=False)

        message_data_list = []

        for message in messages:
            message_data = self.format_message(message, message.sender)
            message_data_list.append(message_data)

            # Запускаем задачу перевода асинхронно
            translate_message.delay(message.id, message.content, self.language, self.channel_name)

        return message_data_list

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
    async def connect(self):
        self.connected_at = timezone.now()
        await super().connect()

    async def receive(self, text_data):
        self.message_received_at = timezone.now()
        await super().receive(text_data)
        await self.update_response_time()

    @database_sync_to_async
    def update_response_time(self):
        user = self.scope['user']
        if hasattr(user, 'lessor'):
            response_time = self.message_received_at - self.connected_at
            lessor = user.lessor

            if lessor.average_response_time is None:
                lessor.average_response_time = response_time
            else:
                total_response_time = lessor.average_response_time * lessor.count_trip
                total_response_time += response_time
                lessor.count_trip += 1
                lessor.average_response_time = total_response_time / lessor.count_trip

            lessor.save()

    def get_chat_instance(self):
        return Chat.objects.select_related(
            'trip__organizer', 'trip__content_type'
        ).only(
            'id', 'trip__id', 'trip__organizer__id', 'trip__content_type__id', 'trip__object_id'
        ).get(id=self.chat_id)

    def get_chat_model(self):
        return Chat

    def create_message_instance(self, chat, user, message_content, file):
        return Message.objects.create(chat=chat, sender=user, content=message_content, file=file)

    def get_messages_queryset(self, chat):
        return chat.messages.order_by('timestamp').select_related(
            'sender'
        ).only(
            'id', 'chat_id', 'sender_id', 'content', 'timestamp', 'file',
            'sender__id', 'sender__first_name', 'sender__avatar', 'deleted'
        )

    def check_user_access(self, user, chat):
        if user.role in ['admin', 'manager']:
            return True

        is_franchise_director = (
                hasattr(chat.trip.vehicle, 'owner') and
                chat.trip.vehicle.owner.lessor.franchise and
                chat.trip.vehicle.owner.lessor.franchise.director == user
        )

        return (
                user in chat.participants.all() or
                user == chat.trip.organizer or
                user == chat.trip.vehicle.owner or
                is_franchise_director
        )

    async def chat_message_translated(self, event):
        """
        Обработчик для переведенных сообщений
        """
        message_id = event['message_id']
        translated_content = event['translated_content']

        # Отправляем обновленное сообщение клиенту
        await self.send(text_data=json.dumps({
            'type': 'message_translated',
            'message_id': message_id,
            'translated_content': translated_content
        }))
        

class ChatSupportConsumer(BaseChatConsumer):
    def get_chat_instance(self):
        return self.get_chat_model().objects.select_related('creator', 'topic').get(id=self.chat_id)

    def get_chat_model(self):
        return ChatSupport

    def create_message_instance(self, chat, user, message_content, file):
        return MessageSupport.objects.create(support_chat=chat, sender=user, content=message_content, file=file)

    def get_messages_queryset(self, chat):
        return chat.message_support.select_related('sender').order_by('timestamp')

    def check_user_access(self, user, chat):
        if user.is_superuser or user.is_staff:
            return True
        return chat.creator == user

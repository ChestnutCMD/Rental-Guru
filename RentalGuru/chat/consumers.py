import logging

from django.db import transaction
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
logger = logging.getLogger(__name__)


class BaseChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'

        query_params = dict(x.split('=') for x in self.scope['query_string'].decode().split('&'))
        token = query_params.get('token')
        self.language = query_params.get('lang', 'en')

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
        try:
            data = json.loads(text_data)

            # Handle simple message format
            if 'message' in data and isinstance(data['message'], str):
                await self.handle_send_message({'message': data['message']})
                return

            # Handle message with file
            if 'message' in data and isinstance(data['message'], dict):
                await self.handle_send_message(data['message'])
                return

            # Handle message deletion
            if 'delete' in data:
                success = await self.handle_delete_message({'message_id': data['delete']})
                if not success:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to delete message'
                    }))
                return

            # Handle message update
            if 'update' in data and 'content' in data:
                success = await self.handle_update_message({
                    'message_id': data['update'],
                    'new_content': data['content']
                })
                if not success:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to update message'
                    }))
                return

            # Legacy format support
            action = data.get('action')
            if action:
                if action == 'send_message':
                    await self.handle_send_message(data)
                elif action == 'update_message':
                    await self.handle_update_message(data)
                elif action == 'delete_message':
                    await self.handle_delete_message(data)

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    async def handle_send_message(self, data):
        message_content = data.get('message') if isinstance(data.get('message'), str) else data.get('content', '')
        file = data.get('file')
        user = self.scope['user']

        logger.info(f"Original message: {message_content}")

        try:
            translated_message_content = translator.translate(message_content, dest=self.language).text
        except Exception as e:
            logger.error(f"Error during translation: {e}")
            translated_message_content = message_content

        logger.info(f"Translated message: {translated_message_content}")

        try:
            message = await self.save_message(user, translated_message_content, file)
            message_data = self.format_message(message, user)

            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    'type': 'chat_message',
                    'message': message_data,
                    'action': 'new'
                }
            )
            return True
        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")
            return False

    async def handle_update_message(self, data):
        try:
            message_id = data.get('message_id')
            new_content = data.get('new_content')
            user = self.scope['user']

            updated_message = await self.update_message(message_id, user, new_content)
            if updated_message:
                message_data = self.format_message(updated_message, user)
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        'type': 'chat_message',
                        'message': message_data,
                        'action': 'update'
                    }
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating message: {str(e)}")
            return False

    async def handle_delete_message(self, data):
        try:
            message_id = data.get('message_id')
            user = self.scope['user']

            if await self.delete_message(message_id, user):
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        'type': 'chat_message',
                        'message_id': message_id,
                        'action': 'delete'
                    }
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting message: {str(e)}")
            return False

    @database_sync_to_async
    def save_message(self, user, message_content, file=None):
        chat = self.get_chat_instance()
        message = self.create_message_instance(chat, user, message_content, file)
        return message

    @database_sync_to_async
    def update_message(self, message_id, user, new_content):
        with transaction.atomic():
            try:
                message = Message.objects.select_for_update().get(
                    id=message_id,
                    sender=user,
                    deleted=False
                )
                message.content = new_content
                message.save()
                return message
            except Message.DoesNotExist:
                return None

    @database_sync_to_async
    def delete_message(self, message_id, user):
        with transaction.atomic():
            try:
                message = Message.objects.select_for_update().get(
                    id=message_id,
                    sender=user,
                    deleted=False
                )
                message.deleted = True
                message.save()
                return True
            except Message.DoesNotExist:
                return False

    async def chat_message(self, event):
        action = event.get('action', 'new')

        if action == 'delete':
            await self.send(text_data=json.dumps({
                'type': 'delete',
                'message_id': event['message_id']
            }))
        else:
            await self.send(text_data=json.dumps({
                'type': action,
                'message': event['message']
            }, ensure_ascii=False))

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
                (hasattr(chat.request_rent.vehicle, 'owner') and
                 chat.request_rent.vehicle.owner.lessor.franchise and
                 chat.request_rent.vehicle.owner.lessor.franchise.director == user)
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
        }, ensure_ascii=False))

    def format_message(self, message, user):
        return {
            'id': message.id,
            'sender': {
                'id': user.id,
                'first_name': user.first_name,
                'avatar': user.avatar.url if user.avatar else None,
            },
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'file': message.file.url if message.file else None,
            'deleted': message.deleted
        }

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
            'request_rent__organizer', 'request_rent__content_type'
        ).only(
            'id', 'request_rent__id', 'request_rent__organizer__id', 'request_rent__content_type__id', 'request_rent__object_id'
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
                hasattr(chat.request_rent.vehicle, 'owner') and
                chat.request_rent.vehicle.owner.lessor.franchise and
                chat.request_rent.vehicle.owner.lessor.franchise.director == user
        )

        return (
                user in chat.participants.all() or
                user == chat.request_rent.organizer or
                user == chat.request_rent.vehicle.owner or
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
        }, ensure_ascii=False))
        

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

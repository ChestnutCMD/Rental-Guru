import base64
import io
import logging

from asgiref.sync import sync_to_async
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db import transaction
from django.utils import timezone
from googletrans import Translator
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import json

from RentalGuru.settings import HOST_URL
from chat.models import MessageSupport, ChatSupport, Message, Chat
from notification.models import Notification
from .tasks import translate_message

translator = Translator()
logger = logging.getLogger(__name__)


class BaseChatConsumer(AsyncWebsocketConsumer):
    """ Базовый чат от кторого наследуются чат на аренду и чат с техподдержкой"""
    async def connect(self):
        """ Обработка соединения с чатом """
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
        """ Проверка токена """
        validated_token = JWTAuthentication().get_validated_token(token)
        return JWTAuthentication().get_user(validated_token)

    async def disconnect(self, close_code):
        """ Отключение от чата """
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def fetch_messages(self, offset=0, limit=20):
        """ Получение сообщений с пагинацией """
        chat = self.get_chat_instance()
        messages_queryset = self.get_messages_queryset(chat)

        messages = await database_sync_to_async(lambda: list(
            messages_queryset.order_by('-timestamp')[offset:offset + limit]
        ))()

        formatted_messages = [
            self.format_message(message, self.scope['user']) for message in messages
        ]
        return formatted_messages

    async def receive(self, text_data):
        """ Обработка сообщений в сокете """
        try:
            data = json.loads(text_data)

            # Проверяем наличие типа сообщения
            if 'type' not in data:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Missing "type" field in message'
                }))
                return

            if data['type'] == 'load_previous_messages':
                offset = data.get('offset', 0)
                limit = data.get('limit', 20)
                previous_messages = await self.load_previous_messages(offset, limit)
                await self.send(text_data=json.dumps({
                    'type': 'previous_messages',
                    'messages': previous_messages,
                }))

            elif 'message' in data and isinstance(data['message'], str):
                await self.handle_send_message({'message': data['message']})
                return

            elif 'message' in data and isinstance(data['message'], dict):
                await self.handle_send_message(data['message'])
                return

            elif 'delete' in data:
                success = await self.handle_delete_message({'message_id': data['delete']})
                if not success:
                    await self.send(text_data=json.dumps({
                        'type': 'error',
                        'message': 'Failed to delete message'
                    }))
                return

            elif 'update' in data and 'content' in data:
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
        user = self.scope['user']

        base64_file = data.get('file')
        file = None
        if base64_file:
            logger.info(f"Received data: {data}")
            try:
                file_data = base64.b64decode(
                    base64_file.split(',')[-1])  # Используйте split(',')[-1] для удаления префикса
                file_name = data.get('name', 'unnamed_file')
                content_type = data.get('type', 'application/octet-stream')

                file = InMemoryUploadedFile(
                    file=io.BytesIO(file_data),
                    field_name=None,
                    name=file_name,
                    content_type=content_type,
                    size=len(file_data),
                    charset=None
                )
                logger.info(f"File name: {file_name}, size: {len(file_data)}, type: {content_type}")
            except Exception as e:
                logger.error(f"Error decoding base64 file: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to decode the uploaded file'
                }))
                return False

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
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
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
            print(message_id)
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

    async def load_previous_messages(self, offset, limit):
        """Загрузка предыдущих сообщений с учетом offset и limit"""
        messages = await self.get_previous_messages(offset, limit)
        return messages

    @database_sync_to_async
    def save_message(self, user, message_content, file=None):
        chat = self.get_chat_instance()
        logger.info(f"Chat instance: {chat}")
        logger.info(f"Chat type: {type(chat)}")
        logger.info(f"User: {user}")
        logger.info(f"Message content: {message_content}")
        logger.info(f"File: {file}")
        message = self.create_message_instance(chat, user, message_content, file)
        logger.info(f"Created message: {message}")
        return message

    @database_sync_to_async
    def update_message(self, message_id, user, new_content):
        with transaction.atomic():
            try:
                message = self.get_messages_objects().objects.select_for_update().get(
                    id=message_id,
                    sender=user,
                    deleted=False
                )
                message.content = new_content
                message.save()
                return message
            except self.get_messages_objects().DoesNotExist:
                return None

    @database_sync_to_async
    def delete_message(self, message_id, user):
        with transaction.atomic():

            try:
                message = self.get_messages_objects().objects.select_for_update().get(
                    id=message_id,
                    sender=user,
                    deleted=False
                )
                message.deleted = True
                message.save()
                return True
            except self.get_messages_objects().DoesNotExist:
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
    def get_previous_messages(self, offset=0, limit=20):
        """Получение предыдущих сообщений с поддержкой пагинации"""
        chat = self.get_chat_instance()
        user = self.scope['user']

        if hasattr(chat, 'request_rent'):
            show_all_messages = (
                    user.role in ['admin', 'manager'] or
                    (hasattr(chat.request_rent.vehicle, 'owner') and
                     chat.request_rent.vehicle.owner.lessor.franchise and
                     chat.request_rent.vehicle.owner.lessor.franchise.director == user)
            )
        else:
            show_all_messages = user.role in ['admin', 'manager']

        messages_queryset = self.get_messages_queryset(chat)

        if not show_all_messages:
            messages_queryset = messages_queryset.filter(deleted=False)

        messages = messages_queryset.order_by('-timestamp')[offset:offset + limit]

        message_data_list = []

        for message in reversed(messages):
            message_data = self.format_message(message, message.sender)
            message_data_list.append(message_data)

            translate_message.delay(message.id, message.content, self.language, self.channel_name)

        return message_data_list

    async def send_previous_messages(self):
        previous_messages = await self.get_previous_messages()
        await self.send(text_data=json.dumps({
            'type': 'previous_messages',
            'messages': previous_messages
        }, ensure_ascii=False))

    def format_message(self, message, user):
        """ Форматирование сообщений """
        return {
            'id': message.id,
            'sender': {
                'id': user.id,
                'first_name': user.first_name,
                'avatar': user.avatar.url if user.avatar else None,
            },
            'content': message.content,
            'timestamp': message.timestamp.isoformat(),
            'file': f"{HOST_URL}{message.file.url}" if message.file else None,
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

    def get_messages_objects(self):
        raise NotImplementedError

class ChatConsumer(BaseChatConsumer):
    """ Чат по аренде """
    async def connect(self):
        self.connected_at = timezone.now()
        await super().connect()

    async def receive(self, text_data):
        data = json.loads(text_data)

        if 'update_request_rent' in data:
            data['status'] = 'unknown'
            success = await self.handle_request_rent_update(data['update_request_rent'])
            if success:
                await self.send(text_data=json.dumps({
                    'type': 'update_success',
                    'message': 'RequestRent updated successfully.'
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to update RequestRent.'
                }))
        elif 'update_status' in data:
            new_status = data['update_status']
            success = await self.handle_request_rent_status_update(new_status)
            if success:
                await self.send(text_data=json.dumps({
                    'type': 'status_update_success',
                    'message': f"Status updated to {new_status}."
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to update status.'
                }))
        else:
            await super().receive(text_data)

    async def handle_request_rent_update(self, update_data):
        """ Обновление заявки на аренду арендодателем """
        user = self.scope['user']
        chat = await database_sync_to_async(self.get_chat_instance)()
        request_rent = chat.request_rent

        is_owner = await database_sync_to_async(lambda: user == request_rent.vehicle.owner)()
        has_availability = await self.has_on_request_availability(request_rent.vehicle)
        request_status = await self.check_request_status(request_rent)

        if is_owner and has_availability and request_status:
            request_rent.status = 'unknown'

            fields_to_update = ['start_time', 'end_time', 'start_date', 'end_date', 'total_cost']
            for field in fields_to_update:
                if field in update_data:
                    setattr(request_rent, field, update_data[field])

            if 'content_type' in update_data:
                content_type = await self.get_content_type(update_data['content_type'])
                request_rent.content_type = content_type

            if 'object_id' in update_data:
                request_rent.object_id = update_data['object_id']

            await database_sync_to_async(request_rent.save)()

            message_content = {
                "start_time": request_rent.start_time,
                "end_time": request_rent.end_time,
                "start_date": request_rent.start_date,
                "end_date": request_rent.end_date,
                "total_cost": request_rent.total_cost,
                "status": request_rent.status,
                "content_type": request_rent.content_type,
                "object_id": request_rent.object_id
            }
            await self.handle_send_message({'message': json.dumps(message_content, ensure_ascii=False)})

            return True
        return False

    @database_sync_to_async
    def check_request_status(self, request_rent):
        return request_rent.status in ['unknown', 'denied']

    @database_sync_to_async
    def has_on_request_availability(self, vehicle):
        return vehicle.availabilities.filter(on_request=True).exists()

    async def handle_request_rent_status_update(self, update_data):
        """ Обновление статуса заявки на аренду от арендатора """
        user = self.scope['user']
        chat = await database_sync_to_async(self.get_chat_instance)()
        request_rent = chat.request_rent

        is_organizer = await database_sync_to_async(lambda: user == request_rent.organizer)()
        if not is_organizer:
            return False

        new_status = update_data.get('status')
        valid_statuses = ['accept', 'denied']
        if new_status not in valid_statuses:
            return False

        if new_status == 'accept':
            fields_valid = await self.check_request_rent_fields(request_rent)
            if not fields_valid:
                return False

        request_rent.status = new_status
        await database_sync_to_async(request_rent.save)()

        if new_status == 'accept':
            vehicle_owner = await database_sync_to_async(lambda: request_rent.vehicle.owner)()
            await self.create_notification(vehicle_owner, "Статус вашей заявки на аренду был принят.")

        status_display = {
            'accept': 'Принято',
            'denied': 'Отклонено'
        }
        message_content = f"Статус заявки был обновлён на: **{status_display.get(new_status, new_status)}**."
        await self.handle_send_message({'message': message_content})
        return True

    @database_sync_to_async
    def create_notification(self, user, content):
        """Создает уведомление для пользователя."""
        Notification.objects.create(user=user, content=content)

    @database_sync_to_async
    def check_request_rent_fields(self, request_rent):
        """Проверяет, что поля не равны None и total_cost больше 0."""
        return all([
            request_rent.start_time is not None,
            request_rent.end_time is not None,
            request_rent.start_date is not None,
            request_rent.end_date is not None,
            request_rent.total_cost > 0
        ])

    async def send_status_update_message(self, chat, message_content):
        """Создает и отправляет сообщение в чат о статусе заявки."""
        user = self.scope['user']
        message = await database_sync_to_async(self.create_message_instance)(chat, user, json.dumps(message_content, ensure_ascii=False), file=None)
        message_data = self.format_message(message, user)

        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'chat_message',
                'message': message_data,
                'action': 'status_update'
            }
        )

    @database_sync_to_async
    def get_content_type(self, model_name):
        return ContentType.objects.get(model=model_name.lower())

    @database_sync_to_async
    def update_response_time(self):
        """ Обновление среднего времени ответа арендодателя"""
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
        """ Обработчик для переведенных сообщений """
        message_id = event['message_id']
        translated_content = event['translated_content']

        await self.send(text_data=json.dumps({
            'type': 'message_translated',
            'message_id': message_id,
            'translated_content': translated_content
        }, ensure_ascii=False))

    def get_messages_objects(self):
        return Message


class ChatSupportConsumer(BaseChatConsumer):
    """ Чат техподдержки """
    def get_chat_instance(self):
        return self.get_chat_model().objects.select_related('creator').get(id=self.chat_id)

    def get_chat_model(self):
        return ChatSupport

    def get_messages_objects(self):
        return MessageSupport

    def create_message_instance(self, chat, user, message_content, file):
        return MessageSupport.objects.create(chat=chat, sender=user, content=message_content, file=file)

    def get_messages_queryset(self, chat):
        return chat.message_support.select_related('sender').order_by('timestamp')

    def check_user_access(self, user, chat):
        if user.is_superuser or user.is_staff:
            return True
        return chat.creator == user

    async def chat_message_translated(self, event):
        """ Обработчик для переведенных сообщений """
        message_id = event['message_id']
        translated_content = event['translated_content']

        await self.send(text_data=json.dumps({
            'type': 'message_translated',
            'message_id': message_id,
            'translated_content': translated_content
        }, ensure_ascii=False))

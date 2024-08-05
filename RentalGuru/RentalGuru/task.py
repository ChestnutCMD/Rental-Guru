import os
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from pyfcm import FCMNotification

from app.models import FCMToken, User
import logging

logger = logging.getLogger(__name__)

# @shared_task
# def send_web_push_notification(user_id, notification_title, notification_body):
#     tokens = FCMToken.objects.filter(user_id=user_id).values_list('token', flat=True)
#     push_service = FCMNotification(service_account_file=os.getenv('SERVICE_ACCOUNT_FILE'), project_id=os.getenv('PROJECT_ID'))
#
#     notification_image = "logo.png"
#     for token in tokens:
#         result = push_service.notify(
#             fcm_token=token,
#             notification_title=notification_title,
#             notification_body=notification_body,
#             notification_image=notification_image)
#
#         # Обработка результата
#         if 'failure' in result and result['failure'] > 0:
#             for result_token, result_data in zip(result['results'], tokens):
#                 if 'error' in result_data:
#                     error = result_data['error']
#                     if error in ['InvalidRegistration', 'NotRegistered']:
#                         # Удаление недействительных токенов
#                         FCMToken.objects.filter(token=result_token).delete()
#     return "Notifications sent"


@shared_task
def send_web_push_notification(user_id, title, body):
    try:
        user = User.objects.get(id=user_id)
        fcm_token = FCMToken.objects.filter(user=user).values_list('token', flat=True).first()

        if not fcm_token:
            logger.error(f"No FCM token found for user {user.id}")
            return

        # Конфигурация FCM
        push_service = FCMNotification(
            service_account_file=os.getenv('SERVICE_ACCOUNT_FILE'),
            project_id=os.getenv('PROJECT_ID')
        )

        # Сообщение
        message = {
            "title": title,
            "body": body
        }

        # Отправка уведомления
        result = push_service.notify_single_device(
            registration_id=fcm_token,
            message_title=title,
            message_body=body
        )

        logger.info(f"Notification sent to user {user.id}: {result}")
        return result

    except Exception as e:
        logger.exception(f"Error sending notification to user {user_id}: {e}")
        raise


# @shared_task
# def remove_old_tokens():
#     expiration_date = timezone.now() - timedelta(days=90)  # Удаляем токены старше 90 дней
#     FCMToken.objects.filter(last_used_at__lt=expiration_date).delete()
#
#
# @shared_task
# def add(x, y):
#     return x + y

import os
from datetime import timedelta
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from pyfcm import FCMNotification

from RentalGuru import settings
from app.models import User
from notification.models import Notification, FCMToken


@shared_task
def send_email_notification(notification_id):
    notification = Notification.objects.select_related('user').get(id=notification_id)
    message = f'{notification.content}\n{notification.url}'
    send_mail(
        subject='Rental-Guru',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[notification.user.email],
        fail_silently=False,
    )


@shared_task
def send_web_push_notification(user_id,  notification_body, notification_url):
    user = User.objects.prefetch_related('fcmtoken_set').get(id=user_id)
    tokens = user.fcmtoken_set.values_list('token', flat=True)
    push_service = FCMNotification(service_account_file=os.getenv('SERVICE_ACCOUNT_FILE'), project_id=os.getenv('PROJECT_ID'))
    notification_title = 'Rental-Guru'
    notification_image = 'logo.png'

    data_payload = {
        "click_action": "FLUTTER_NOTIFICATION_CLICK",
        "url": notification_url
    }

    for token in tokens:
        result = push_service.notify(
            fcm_token=token,
            notification_title=notification_title,
            notification_body=notification_body,
            notification_image=notification_image,
            data_payload=data_payload
        )

        # Обработка результата
        if 'failure' in result and result['failure'] > 0:
            for result_token, result_data in zip(result['results'], tokens):
                if 'error' in result_data:
                    error = result_data['error']
                    if error in ['InvalidRegistration', 'NotRegistered']:
                        # Удаление недействительных токенов
                        FCMToken.objects.filter(token=result_token).delete()
    return "Notifications sent"


@shared_task
def remove_old_tokens():
    expiration_date = timezone.now() - timedelta(days=90)  # Удаляем токены старше 90 дней
    FCMToken.objects.filter(last_used_at__lt=expiration_date).delete()
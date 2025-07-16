import json
import os
from datetime import timedelta

import requests
from celery import shared_task
from django.apps import apps
from django.core.mail import send_mail
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from pyfcm import FCMNotification
from django.db import models

from RentalGuru.settings import DEFAULT_FROM_EMAIL, AUTH_USER_MODEL, HOST_URL


class Notification(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    content = models.CharField(max_length=255, verbose_name='Сообщение')
    read_it = models.BooleanField(default=False, verbose_name='Прочитано')
    url = models.URLField(max_length=1000, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def get_absolute_url(self):
        return f'{HOST_URL}/notifications/{self.pk}'

    def send_notification(self):
        if self.user.email_notification:
            send_email_notification.delay(self.id)
        if self.user.push_notification:
            url = self.get_absolute_url()
            self.content = f'{self.content}\n{url}'
            send_web_push_notification.delay(self.user.id, self.content, self.url)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.send_notification()

    def __str__(self):
        return str(self.content)


class FCMToken(models.Model):
    user = models.ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    token = models.CharField(max_length=255, unique=True, verbose_name='Токен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    last_used_at = models.DateTimeField(auto_now=True, verbose_name='Последнее использование')

    class Meta:
        verbose_name = 'FCM токен'
        verbose_name_plural = 'FCM токены'

    def __str__(self):
        return str(self.token)


@shared_task
def send_email_notification(notification_id):
    notification = Notification.objects.select_related('user').get(id=notification_id)
    if notification.url:
        message = f'{notification.content}\n{notification.url}'
    else:
        message = f'{notification.content}'
    send_mail(
        subject='Rental-Guru',
        message=message,
        from_email=DEFAULT_FROM_EMAIL,
        recipient_list=[notification.user.email],
        fail_silently=False,
    )
    return "Email notifications sent"


@shared_task
def send_web_push_notification(user_id, notification_body, notification_url=None):
    User = apps.get_model(AUTH_USER_MODEL)
    user = User.objects.prefetch_related('fcmtoken_set').get(id=user_id)
    tokens = list(user.fcmtoken_set.values_list('token', flat=True))

    if not tokens:
        return "No FCM tokens for user"

    # Получаем access_token через сервисный аккаунт
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("SERVICE_ACCOUNT_FILE"),
        scopes=["https://www.googleapis.com/auth/firebase.messaging"],
    )
    credentials.refresh(Request())
    access_token = credentials.token

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; UTF-8",
    }

    fcm_url = f"https://fcm.googleapis.com/v1/projects/{os.getenv('PROJECT_ID')}/messages:send"

    for token in tokens:
        message = {
            "message": {
                "token": token,
                "notification": {
                    "title": "Rental-Guru",
                    "body": notification_body
                },
                "data": {
                    "click_action": "FLUTTER_NOTIFICATION_CLICK",
                    "url": notification_url or ""
                },
                "webpush": {
                    "headers": {
                        "Urgency": "high"
                    },
                    "notification": {
                        "icon": "https://rentalguru.ru/static/firebase-logo.png",
                        "click_action": notification_url or "https://rentalguru.ru"
                    }
                }
            }
        }

        response = requests.post(fcm_url, headers=headers, data=json.dumps(message))

        if response.status_code == 403:
            # Удаляем невалидный токен
            FCMToken.objects.filter(token=token).delete()
        elif response.status_code == 400 and "unregistered" in response.text:
            FCMToken.objects.filter(token=token).delete()
        elif not response.ok:
            raise Exception(f"Failed to send notification: {response.status_code} {response.text}")

    return "Push notifications sent"


@shared_task
def remove_old_tokens():
    expiration_date = timezone.now() - timedelta(days=90)
    FCMToken.objects.filter(last_used_at__lt=expiration_date).delete()

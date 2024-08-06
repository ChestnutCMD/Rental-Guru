import os
from datetime import timedelta
from celery import shared_task
from django.core.mail import send_mail
from django.db import models
from django.utils import timezone
from pyfcm import FCMNotification

from RentalGuru import settings
from app.models import User


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    content = models.CharField(max_length=255, verbose_name='Сообщение')
    read_it = models.BooleanField(default=False, verbose_name='Прочитано')

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def get_absolute_url(self):
        return f'https://saqartvel.ru/notifications/{self.pk}'

    def send_notification(self):
        if self.user.email_notification:
            send_email_notification.delay(self.id)
        if self.user.push_notification:
            url = self.get_absolute_url()
            self.content = f'{self.content}\n{url}'
            send_web_push_notification.delay(self.user.id, self.content)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.send_notification()

    def __str__(self):
        return str(self.content)


class FCMToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    token = models.CharField(max_length=255, unique=True, verbose_name='Токен')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создан')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлен')
    last_used_at = models.DateTimeField(auto_now=True, verbose_name='Последнее использование')


@shared_task
def send_email_notification(notification_id):
    notification = Notification.objects.select_related('user').get(id=notification_id)
    notification.content = f'{notification.content}\n{notification.get_absolute_url()}'
    send_mail(
        'Rental-Guru',
        notification.content,
        settings.DEFAULT_FROM_EMAIL,
        [notification.user.email],
        fail_silently=False,
    )


@shared_task
def send_web_push_notification(user_id,  notification_body):
    user = User.objects.prefetch_related('fcmtoken_set').get(id=user_id)
    tokens = user.fcmtoken_set.values_list('token', flat=True)
    push_service = FCMNotification(service_account_file=os.getenv('SERVICE_ACCOUNT_FILE'), project_id=os.getenv('PROJECT_ID'))
    notification_title = 'Rental-Guru'
    notification_image = 'logo.png'

    for token in tokens:
        result = push_service.notify(
            fcm_token=token,
            notification_title=notification_title,
            notification_body=notification_body,
            notification_image=notification_image
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

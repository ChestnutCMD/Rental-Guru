from celery import shared_task
from django.core.mail import send_mail

from RentalGuru import settings


@shared_task
def send_email_password(user_name, user_email, password):
    send_mail(
        subject='Ваш пароль для доступа к Rental Guru',
        message=f'Здравствуйте, {user_name}!\n\nВаш пароль для доступа: {password}\nПожалуйста, измените его при первой возможности.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
        fail_silently=False,
    )


@shared_task
def send_email_reset_password(reset_url, user_email):

    send_mail(
        subject="Восстановление пароля",
        message=f"Используйте следующую ссылку для сброса пароля: {reset_url}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user_email],
    )

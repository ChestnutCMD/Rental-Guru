from celery import shared_task
from django.core.mail import send_mail
from googletrans import Translator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from RentalGuru import settings


@shared_task
def translate_message(message_id, content, dest_language, channel_name):
    translator = Translator()
    try:
        translated_content = translator.translate(content, dest=dest_language).text
    except Exception as e:
        print(f"Error during translation: {e}")
        translated_content = content

    # Отправляем переведенное сообщение обратно через WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.send)(
        channel_name,
        {
            "type": "chat.message.translated",
            "message_id": message_id,
            "translated_content": translated_content
        }
    )


@shared_task
def send_issue_email(issue_id):
    from .models import IssueSupport

    try:
        issue = IssueSupport.objects.select_related('chat__creator', 'topic').get(id=issue_id)

        url = f'wss://{settings.HOST_URL.split("//")[1]}/ws/support_chat/{issue.chat}/'

        subject = 'Новое обращение в техподдержку'
        message = f'Тема: {issue.topic.name}\nОписание: {issue.description}\nОбращение создано.\nСсылка на чат: {url}'

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.DEFAULT_FROM_EMAIL,
            fail_silently=False,
        )
        return f"Email sent to {settings.DEFAULT_FROM_EMAIL}"
    except IssueSupport.DoesNotExist:
        return f"Issue with id {issue_id} does not exist"

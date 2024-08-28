from celery import shared_task
from googletrans import Translator
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


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
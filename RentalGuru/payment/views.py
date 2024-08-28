import hmac
import hashlib
import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from .tasks import process_tinkoff_webhook


@csrf_exempt
@require_POST
def tinkoff_webhook(request):
    # Проверка подписи
    received_token = request.headers.get('Token')
    data = request.body.decode('utf-8')
    calculated_token = hmac.new(
        settings.TINKOFF_SECRET_KEY.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    if received_token != calculated_token:
        return HttpResponse(status=400)

    # Обработка данных вебхука
    payload = json.loads(data)
    payment_id = payload.get('PaymentId')
    status = payload.get('Status')

    process_tinkoff_webhook.delay(payment_id, status)

    return HttpResponse(status=200)

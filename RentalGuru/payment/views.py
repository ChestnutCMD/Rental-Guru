import hashlib

from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from RentalGuru import settings
from chat.models import Chat, Trip
from notification.models import Notification
from payment.TinkoffClient import TinkoffAPI
from payment.models import Payment
from payment.serializers import PaymentSerializer


class PaymentViewSet(viewsets.ViewSet):
    """
    ViewSet для работы с платежами
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        Получение списка всех платежей текущего пользователя
        """
        payments = Payment.objects.filter(request_rent__organizer=request.user)
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """
        Инициализация оплаты платежа через Тинькофф
        """
        try:
            payment = Payment.objects.get(pk=pk, request_rent__organizer=request.user)

            if payment.status != 'pending':
                return Response({'detail': 'Платеж уже обработан или отменен.'}, status=status.HTTP_400_BAD_REQUEST)

            if not payment.request_rent.vehicle:
                return Response({'detail': 'Транспорт не найден для данной заявки.'},
                                status=status.HTTP_400_BAD_REQUEST)

            if not payment.request_rent.id:
                return Response({'detail': 'Некорректная заявка на аренду.'}, status=status.HTTP_400_BAD_REQUEST)

            tinkoff = TinkoffAPI()
            response = tinkoff.create_payment(
                order_id=str(payment.id),
                amount=int(payment.amount * 100),
                description=f'Аренда транспорта {payment.request_rent.vehicle} (заявка #{payment.request_rent.id})'
            )

            if not response.get('PaymentId') or not response.get('PaymentUrl'):
                return Response({'detail': 'Ошибка инициализации платежа в Тинькофф.'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            payment.payment_id = response['PaymentId']
            payment.status = 'pending'
            payment.save()

            return Response({'detail': 'Платеж успешно инициализирован.', 'payment_url': response['PaymentUrl']})
        except Payment.DoesNotExist:
            return Response({'detail': 'Платеж не найден.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TinkoffCallbackView(APIView):
    """
    Обрабатывает callback'и от Тинькофф.
    """
    def verify_signature(self, data):
        """
        Проверяет подпись (Token) в запросе от Тинькофф.
        """
        token = data.get('Token')
        if not token:
            return False

        secret_key = settings.TINYPAY_PASSWORD

        concatenated_params = ''.join(
            str(data[key]) for key in sorted(data.keys()) if key != 'Token'
        )

        calculated_token = hashlib.sha256(f"{secret_key}{concatenated_params}".encode('utf-8')).hexdigest()
        return calculated_token == token

    def post(self, request, *args, **kwargs):
        data = request.data

        # Проверяем подпись
        # if not self.verify_signature(data):
        #     return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

        required_fields = {'PaymentId', 'Status', 'Amount'}
        if not required_fields.issubset(data.keys()):
            return Response({"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

        payment_id = data['PaymentId']
        status_from_tinkoff = data['Status']
        amount = int(data['Amount']) / 100

        payment = get_object_or_404(Payment, payment_id=payment_id)

        if status_from_tinkoff == 'CONFIRMED':
            payment.status = 'success'
            payment.paid_at = now()
            payment.save()

            instance = payment.request_rent
            instance.create_chat()

            chat = Chat.objects.get(request_rent=instance)

            if not Trip.objects.filter(
                    object_id=instance.object_id,
                    start_date=instance.start_date,
                    end_date=instance.end_date
            ).exists():
                Trip.objects.create(
                    organizer=instance.organizer,
                    content_type=instance.content_type,
                    object_id=instance.object_id,
                    start_date=instance.start_date,
                    end_date=instance.end_date,
                    start_time=instance.start_time,
                    end_time=instance.end_time,
                    total_cost=instance.total_cost,
                    chat=chat
                )
            Notification.objects.create(
                user=instance.organizer,
                content=f"Оплачена заявка на аренду {instance.vehicle}. Начало аренды: {instance.start_date}/{instance.start_time}"
            )
            return Response({"message": "Payment confirmed successfully"}, status=status.HTTP_200_OK)

        elif status_from_tinkoff in ['CANCELLED', 'REJECTED']:
            payment.status = 'failed'
            payment.save()
            Notification.objects.create(
                user=payment.request_rent.organizer,
                content=f"Не удалось обработать платеж #{payment_id} по заявке #{payment.request_rent.id}"
            )
            return Response({"message": f"Payment failed with status {status_from_tinkoff}"}, status=status.HTTP_200_OK)

        return Response({"message": "Unhandled status"}, status=status.HTTP_400_BAD_REQUEST)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import TinkoffAPI


class PaymentView(APIView):
    def post(self, request, *args, **kwargs):
        amount = request.data.get('amount')
        order_id = request.data.get('order_id')
        description = request.data.get('description')

        tinkoff_api = TinkoffAPI()
        response = tinkoff_api.init_payment(amount, order_id, description)

        if response.get('Success'):
            return Response(response, status=status.HTTP_200_OK)
        else:
            return Response(response, status=status.HTTP_400_BAD_REQUEST)


class TinkoffWebhookView(APIView):
    def post(self, request, *args, **kwargs):
        # Обработка данных, пришедших в вебхуке
        data = request.data
        # Изменить статус заказа на основании PaymentId
        return Response(status=status.HTTP_200_OK)

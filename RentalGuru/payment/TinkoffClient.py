import hashlib
import logging
import requests

from RentalGuru.settings import TINYPAY_TERMINAL_KEY, TINYPAY_PASSWORD, TINYPAY_SUCCESS_URL, TINYPAY_FAIL_URL, HOST_URL

logger = logging.getLogger('payment')


class TinkoffAPI:
    def __init__(self):
        self.base_url = 'https://securepay.tinkoff.ru/v2/'
        self.terminal_key = TINYPAY_TERMINAL_KEY
        self.secret_key = TINYPAY_PASSWORD
        self.success_url = TINYPAY_SUCCESS_URL
        self.fail_url = TINYPAY_FAIL_URL

    def _generate_token(self, params):
        """Генерация токена для подписи по спецификации Тинькофф"""
        token_string = (
                str(params.get("Amount", "")) +
                str(params.get("Description", "")) +
                str(params.get("FailURL", "")) +  #
                str(params.get("NotificationURL", "")) +  #
                str(params.get("OrderId", "")) +
                self.secret_key +
                str(params.get("SuccessURL", "")) +  #
                str(params.get('TerminalKey', ""))
        )

        logger.debug(f"Token string (first/last 10 chars): {token_string[:10]}...{token_string[-10:]}")

        return hashlib.sha256(token_string.encode("utf-8")).hexdigest()

    def create_payment(self, order_id, amount, description):
        """Создание платежа"""
        payload = {
            'TerminalKey': self.terminal_key,
            'Amount': amount,
            'OrderId': order_id,
            'Description': description,
            'SuccessURL': self.success_url,
            'FailURL': self.fail_url,
            "NotificationURL": f"{HOST_URL}/payment/callback/"
        }
        payload['Token'] = self._generate_token(payload)
        response = requests.post(f'{self.base_url}Init', json=payload)
        response.raise_for_status()
        return response.json()

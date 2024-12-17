import hashlib

import requests

from RentalGuru.settings import TINYPAY_TERMINAL_KEY, TINYPAY_PASSWORD, TINYPAY_SUCCESS_URL, TINYPAY_FAIL_URL


class TinkoffAPI:
    def __init__(self):
        self.base_url = 'https://securepay.tinkoff.ru/v2/'
        self.terminal_key = TINYPAY_TERMINAL_KEY
        self.secret_key = TINYPAY_PASSWORD
        self.success_url = TINYPAY_SUCCESS_URL
        self.fail_url = TINYPAY_FAIL_URL

    def _generate_token(self, params):
        """Генерация токена для подписи"""
        sorted_params = sorted((k, str(v)) for k, v in params.items() if k != 'Token')
        token_string = ''.join(val for _, val in sorted_params) + self.secret_key
        return hashlib.sha256(token_string.encode('utf-8')).hexdigest()

    def create_payment(self, order_id, amount, description):
        """Создание платежа"""
        payload = {
            'TerminalKey': self.terminal_key,
            'OrderId': order_id,
            'Amount': amount,
            'Description': description,
            'SuccessURL': self.success_url,
            'FailURL': self.fail_url,
        }
        payload['Token'] = self._generate_token(payload)
        response = requests.post(f'{self.base_url}Init', json=payload)
        response.raise_for_status()
        return response.json()

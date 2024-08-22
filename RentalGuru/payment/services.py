import requests
from django.conf import settings
import hashlib


class TinkoffAPI:
    def __init__(self):
        self.terminal_key = settings.TINYPAY_TERMINAL_KEY
        self.password = settings.TINYPAY_PASSWORD
        self.api_url = settings.TINYPAY_API_URL

    def generate_token(self, params):
        token_str = ''.join(str(params[key]) for key in sorted(params.keys()) if key != 'Token')
        token_str += self.password
        return hashlib.sha256(token_str.encode('utf-8')).hexdigest()

    def init_payment(self, amount, order_id, description):
        params = {
            'TerminalKey': self.terminal_key,
            'Amount': amount,
            'OrderId': order_id,
            'Description': description,
            'Password': self.password
        }
        params['Token'] = self.generate_token(params)
        response = requests.post(f'{self.api_url}Init', json=params)
        return response.json()

    def confirm_payment(self, payment_id):
        params = {
            'TerminalKey': self.terminal_key,
            'PaymentId': payment_id,
        }
        params['Token'] = self.generate_token(params)
        response = requests.post(f'{self.api_url}Confirm', json=params)
        return response.json()

    def cancel_payment(self, payment_id):
        params = {
            'TerminalKey': self.terminal_key,
            'PaymentId': payment_id,
        }
        params['Token'] = self.generate_token(params)
        response = requests.post(f'{self.api_url}Cancel', json=params)
        return response.json()
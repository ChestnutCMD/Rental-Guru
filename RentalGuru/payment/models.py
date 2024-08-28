from django.db import models
from django.conf import settings
from chat.models import RequestRent, Trip


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('deposit', 'Депозит'),
        ('full_payment', 'Полная оплата'),
        ('refund', 'Возврат'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    request_rent = models.ForeignKey(RequestRent, on_delete=models.SET_NULL, null=True, blank=True)
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    tinkoff_payment_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PaymentSetting(models.Model):
    franchise_commission = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    platform_commission = models.DecimalField(max_digits=5, decimal_places=2, default=4.00)
    influencer_commission = models.DecimalField(max_digits=5, decimal_places=2, default=40.00)
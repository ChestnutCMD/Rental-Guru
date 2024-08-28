from celery import shared_task
from .models import Transaction
from chat.views import TripViewSet

@shared_task
def process_tinkoff_webhook(payment_id, status):
    try:
        transaction = Transaction.objects.get(tinkoff_payment_id=payment_id)
    except Transaction.DoesNotExist:
        return

    if status == 'CONFIRMED':
        transaction.status = 'completed'
        transaction.save()

        if transaction.transaction_type == 'deposit':
            request_rent = transaction.request_rent
            request_rent.deposit_paid = True
            request_rent.save()
        elif transaction.transaction_type == 'full_payment':
            trip = transaction.trip
            trip.status = 'finished'
            trip.save()
            TripViewSet.distribute_funds(trip, transaction.amount)

    elif status == 'REFUNDED':
        transaction.status = 'refunded'
        transaction.save()

        if transaction.transaction_type == 'deposit':
            request_rent = transaction.request_rent
            request_rent.deposit_paid = False
            request_rent.save()

    elif status in ['REJECTED', 'CANCELED']:
        transaction.status = 'failed'
        transaction.save()
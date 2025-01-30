import django_filters
from chat.models import Message, Trip


class MessageFilter(django_filters.FilterSet):
    chat_id = django_filters.NumberFilter(field_name='chat__id')
    ordering = django_filters.OrderingFilter(fields=['timestamp'])

    class Meta:
        model = Message
        fields = ['chat_id']


class TripFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name='status', label='Статус поездки')

    class Meta:
        model = Trip
        fields = ['status']

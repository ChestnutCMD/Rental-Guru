import django_filters
from chat.models import Message


class MessageFilter(django_filters.FilterSet):
    chat_id = django_filters.NumberFilter(field_name='chat__id')
    ordering = django_filters.OrderingFilter(fields=['timestamp'])

    class Meta:
        model = Message
        fields = ['chat_id']

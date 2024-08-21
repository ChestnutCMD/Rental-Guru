import django_filters
from django.contrib.contenttypes.models import ContentType

from chat.models import Trip


class TripFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(field_name='start_date', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='end_date', lookup_expr='lte')
    type = django_filters.CharFilter(method='filter_by_type')

    class Meta:
        model = Trip
        fields = ['status', 'start_date', 'end_date', 'type']

    def filter_by_type(self, queryset, name, value):
        try:
            content_type = ContentType.objects.get(model=value.lower())
            return queryset.filter(content_type=content_type)
        except ContentType.DoesNotExist:
            return queryset.none()

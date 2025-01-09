from datetime import timedelta
from django.utils import timezone
from django_filters import rest_framework as filters

from app.models import Lessor
from franchise.models import City


class LessorReportFilter(filters.FilterSet):
    period = filters.ChoiceFilter(
        choices=[
            ('day', 'День'),
            ('week', 'Неделя'),
            ('month', 'Месяц'),
            ('quarter', 'Квартал'),
            ('year', 'Год'),
        ],
        method='filter_period'
    )
    city = filters.ModelChoiceFilter(
        queryset=City.objects.all(),
        field_name='user__vehicle__city'
    )
    lessor_id = filters.NumberFilter(field_name='id')

    def filter_period(self, queryset, name, value):
        today = timezone.now().date()

        if value == 'day':
            start_date = today - timedelta(days=1)
        elif value == 'week':
            start_date = today - timedelta(days=7)
        elif value == 'month':
            start_date = today - timedelta(days=30)
        elif value == 'quarter':
            start_date = today - timedelta(days=90)
        elif value == 'year':
            start_date = today - timedelta(days=365)
        else:
            return queryset

        filtered_queryset = queryset.filter(
            user__vehicle__trips__end_date__gte=start_date,
            user__vehicle__trips__end_date__lte=today,
            user__vehicle__trips__status='finished'
        ).distinct()

        from django.db import connection
        print(connection.queries[-1])

        return filtered_queryset

    class Meta:
        model = Lessor
        fields = ['period', 'city', 'lessor_id']

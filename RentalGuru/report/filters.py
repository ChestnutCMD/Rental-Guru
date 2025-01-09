from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
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
        print(f"Фильтр периода: {value}, сегодня: {today}")

        if value == 'day':
            start_date = today
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

        print(f"Дата начала периода: {start_date}")

        vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']
        date_query = Q()

        for vehicle_type in vehicle_types:
            try:
                content_type = ContentType.objects.get(model=vehicle_type)
                date_query |= Q(
                    user__vehicle__trips__content_type=content_type,
                    user__vehicle__trips__end_date__gte=start_date,
                    user__vehicle__trips__status='finished'
                )
            except ContentType.DoesNotExist:
                print(f"ContentType не найден для {vehicle_type}")

        print(f"Сформированный запрос: {date_query}")
        return queryset.filter(date_query).distinct()

    class Meta:
        model = Lessor
        fields = ['period', 'city', 'lessor_id']

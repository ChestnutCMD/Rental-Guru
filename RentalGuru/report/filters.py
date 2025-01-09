from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
from django_filters import rest_framework as filters

from app.models import Lessor
from franchise.models import City


# class LessorReportFilter(filters.FilterSet):
#     period = filters.ChoiceFilter(
#         choices=[
#             ('day', 'День'),
#             ('week', 'Неделя'),
#             ('month', 'Месяц'),
#             ('quarter', 'Квартал'),
#             ('year', 'Год'),
#         ],
#         method='filter_period'
#     )
#     city = filters.ModelChoiceFilter(
#         queryset=City.objects.all(),
#         method='filter_by_city'
#     )
#     lessor = filters.ModelChoiceFilter(
#         queryset=Lessor.objects.all()
#     )
#
#     def filter_by_city(self, queryset, name, value):
#         return queryset.filter(user__vehicle__city=value).distinct()
#
#     def filter_period(self, queryset, name, value):
#         today = timezone.now().date()
#
#         if value == 'day':
#             start_date = today
#         elif value == 'week':
#             start_date = today - timedelta(days=7)
#         elif value == 'month':
#             start_date = today - timedelta(days=30)
#         elif value == 'quarter':
#             start_date = today - timedelta(days=90)
#         elif value == 'year':
#             start_date = today - timedelta(days=365)
#         else:
#             return queryset
#
#         # Фильтруем по периоду через связанные поездки
#         vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']
#         filtered_queryset = queryset.none()
#
#         for vehicle_type in vehicle_types:
#             content_type = ContentType.objects.get(model=vehicle_type)
#             lessors = queryset.filter(
#                 user__vehicle__trips__content_type=content_type,
#                 user__vehicle__trips__end_date__gte=start_date,
#                 user__vehicle__trips__status='finished'
#             ).distinct()
#             filtered_queryset = filtered_queryset.union(lessors)
#
#         return filtered_queryset
#
#     class Meta:
#         model = Lessor
#         fields = ['period', 'city', 'lessor']

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
    lessor_id = filters.NumberFilter(field_name='id')  # Изменено с lessor на lessor_id

    def filter_period(self, queryset, name, value):
        today = timezone.now().date()

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

        vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']
        date_query = Q()

        for vehicle_type in vehicle_types:
            content_type = ContentType.objects.get(model=vehicle_type)
            date_query |= Q(
                user__vehicle__trips__content_type=content_type,
                user__vehicle__trips__end_date__gte=start_date,
                user__vehicle__trips__status='finished'
            )

        return queryset.filter(date_query).distinct()

    class Meta:
        model = Lessor
        fields = ['period', 'city', 'lessor_id']
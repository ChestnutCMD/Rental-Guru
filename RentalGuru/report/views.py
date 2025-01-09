from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.db.models import Sum, Q
from decimal import Decimal

from app.models import Lessor
from chat.models import Trip
from report.filters import LessorReportFilter
from report.permissions import IsAdminRole
from report.serializers import LessorReportSerializer
from vehicle.models import Vehicle


class LessorReportView(ListAPIView):
    serializer_class = LessorReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LessorReportFilter
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        queryset = Lessor.objects.select_related('user').distinct()

        filters = {}

        city = self.request.query_params.get('city')
        if city:
            filters['user__vehicle__city'] = city

        lessor_id = self.request.query_params.get('lessor_id')
        if lessor_id:
            filters['id'] = lessor_id

        if filters:
            queryset = queryset.filter(**filters)

        period = self.request.query_params.get('period')
        if period:
            filter_instance = self.filterset_class()
            queryset = filter_instance.filter_period(queryset, 'period', period)

        return queryset.distinct()

    def get_trips_for_lessor(self, lessor):
        vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']

        base_query = Q(status='finished')

        # period = self.request.query_params.get('period')
        # if period:
        #     today = timezone.now().date()
        #     if period == 'day':
        #         start_date = today
        #     elif period == 'week':
        #         start_date = today - timedelta(days=7)
        #     elif period == 'month':
        #         start_date = today - timedelta(days=30)
        #     elif period == 'quarter':
        #         start_date = today - timedelta(days=90)
        #     elif period == 'year':
        #         start_date = today - timedelta(days=365)
        #
        #     base_query &= Q(end_date__gte=start_date)

        content_type_query = Q()
        for vehicle_type in vehicle_types:
            content_type = ContentType.objects.get(model=vehicle_type)
            vehicles = Vehicle.objects.filter(
                owner=lessor.user,
                polymorphic_ctype=content_type
            ).values_list('id', flat=True)

            if vehicles:
                content_type_query |= Q(
                    content_type=content_type,
                    object_id__in=vehicles
                )

        return Trip.objects.filter(
            content_type_query & base_query
        )

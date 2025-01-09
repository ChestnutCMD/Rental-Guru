from django.contrib.contenttypes.models import ContentType
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
        return Lessor.objects.select_related('user').distinct()

    def get_trips_for_lessor(self, lessor):
        vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']

        # Создаем Q-объект для фильтрации по всем типам транспорта
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

        # Получаем все поездки одним запросом
        return Trip.objects.filter(
            content_type_query,
            status='finished'
        )

    def get_summary_stats(self, queryset):
        total_revenue = Decimal('0.00')
        total_commission = Decimal('0.00')

        for lessor in queryset:
            trips = self.get_trips_for_lessor(lessor)
            revenue = trips.aggregate(
                total=Sum('total_cost', default=Decimal('0.00'))
            )['total']

            total_revenue += revenue
            total_commission += (revenue * lessor.commission) / 100

        return {
            'total_revenue': total_revenue,
            'total_commission': total_commission
        }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        summary = self.get_summary_stats(queryset)

        return Response({
            'lessors': serializer.data,
            'summary': summary
        })

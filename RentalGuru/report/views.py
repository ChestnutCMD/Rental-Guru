from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.db.models import Sum
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
        trips = Trip.objects.none()

        for vehicle_type in vehicle_types:
            content_type = ContentType.objects.get(model=vehicle_type)
            vehicle_trips = Trip.objects.filter(
                content_type=content_type,
                object_id__in=Vehicle.objects.filter(
                    owner=lessor.user
                ).values_list('id', flat=True),
                status='finished'
            )
            trips = trips.union(vehicle_trips)

        return trips

    def get_summary_stats(self, queryset):
        total_revenue = Decimal('0.00')
        total_commission = Decimal('0.00')

        for lessor in queryset:
            trips = self.get_trips_for_lessor(lessor)
            revenue = trips.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

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

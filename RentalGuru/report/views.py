from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.db.models import Sum, Prefetch
from decimal import Decimal

from app.models import Lessor
from chat.models import Trip
from report.filters import LessorReportFilter
from report.permissions import IsAdminRole
from report.serializers import LessorReportSerializer
from vehicle.models import Vehicle


class LessorReportView(ListAPIView):
    permission_classes = [IsAdminRole]
    serializer_class = LessorReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LessorReportFilter

    def get_queryset(self):
        return Lessor.objects.select_related(
            'user'
        ).prefetch_related(
            Prefetch(
                'user__vehicle',
                queryset=Vehicle.objects.select_related('city')
            ),
            Prefetch(
                'user__vehicle__trips',
                queryset=Trip.objects.filter(status='finished')
            )
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        # Подсчет общей статистики
        total_revenue = Decimal('0.00')
        total_commission = Decimal('0.00')

        for lessor in queryset:
            revenue = Trip.objects.filter(
                vehicle__owner=lessor.user,
                status='finished'
            ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

            total_revenue += revenue
            total_commission += (revenue * lessor.commission) / 100

        return Response({
            'lessors': serializer.data,
            'summary': {
                'total_revenue': total_revenue,
                'total_commission': total_commission
            }
        })

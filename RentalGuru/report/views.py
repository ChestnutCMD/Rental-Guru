from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.db.models import Sum
from decimal import Decimal

from app.models import Lessor
from report.filters import LessorReportFilter
from report.permissions import IsAdminRole
from report.serializers import LessorReportSerializer


class LessorReportView(ListAPIView):
    serializer_class = LessorReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = LessorReportFilter
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return Lessor.objects.select_related('user').distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        # Подсчет общей статистики
        total_revenue = Decimal('0.00')
        total_commission = Decimal('0.00')

        for lessor in queryset:
            trips = serializer.get_trips_for_lessor(lessor)
            revenue = trips.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

            total_revenue += revenue
            total_commission += (revenue * lessor.commission) / 100

        return Response({
            'lessors': serializer.data,
            'summary': {
                'total_revenue': total_revenue,
                'total_commission': total_commission
            }
        })

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.db.models import Sum, Q, DecimalField, F, Max
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
        # Оптимизация запросов с использованием select_related и prefetch_related
        queryset = Lessor.objects.select_related('user').prefetch_related(
            'user__vehicle__trips'
        ).annotate(
            revenue=Coalesce(
                Sum(
                    'user__vehicle__trips__total_cost',
                    filter=Q(user__vehicle__trips__status='finished')
                ),
                0
            ),
            last_rental_date=Max(
                'user__vehicle__trips__end_date',
                filter=Q(user__vehicle__trips__status='finished')
            ),
            commission_sum=F('revenue') * F('commission') / 100
        )

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Агрегаты для общей выручки и комиссии
        total_revenue = queryset.aggregate(
            total_revenue=Sum('revenue', output_field=DecimalField())
        )['total_revenue'] or 0

        total_commission = queryset.aggregate(
            total_commission=Sum('commission_sum', output_field=DecimalField())
        )['total_commission'] or 0

        # Сериализация данных
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            "lessors": serializer.data,
            "total_revenue": total_revenue,
            "total_commission": total_commission,
        }, status=status.HTTP_200_OK)
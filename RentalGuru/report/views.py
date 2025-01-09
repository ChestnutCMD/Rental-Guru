from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

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
            queryset = filter_instance.get_filtered_queryset(queryset, period)

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        lessor_ids = queryset.values_list('id', flat=True)

        total_revenue = Decimal('0.00')
        total_commission = Decimal('0.00')

        for lessor in queryset:
            serializer = self.get_serializer(lessor)
            revenue = Decimal(str(serializer.data['total_revenue']))
            commission = Decimal(str(serializer.data['commission_amount']))
            total_revenue += revenue
            total_commission += commission

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            data = result.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        response_data = {
            'total_revenue': round(float(total_revenue), 2),
            'total_commission': round(float(total_commission), 2),
            'lessors_count': queryset.count(),
        }

        if isinstance(data, dict):
            data.update(response_data)
            return Response(data)

        return Response({
            **response_data,
            'results': data
        })

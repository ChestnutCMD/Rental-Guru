from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.generics import ListAPIView

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

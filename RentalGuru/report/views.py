from decimal import Decimal

from django.db.models import Avg
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from app.models import Lessor
from franchise.models import Franchise
from influencer.models import Influencer
from report.filters import LessorReportFilter, InfluencerReportFilter, FranchiseReportFilter
from report.permissions import IsAdminRole
from report.serializers import LessorReportSerializer, InfluencerReportSerializer, FranchiseReportSerializer


@extend_schema(summary="Отчеты. Арендодатели", description="Отчеты. Арендодатели.")
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


@extend_schema(summary="Отчеты. Партнеры", description="Отчеты. Партнеры.")
class InfluencerReportView(ListAPIView):
    serializer_class = InfluencerReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = InfluencerReportFilter
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return Influencer.objects.select_related('user').all()

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.filter_queryset(self.get_queryset())

            # Передаем период и город в контекст сериализатора
            period = request.query_params.get('period')
            city = request.query_params.get('city')
            serializer_context = {
                'period': period,
                'city': city
            }

            # Считаем общие суммы
            total_revenue = Decimal('0.00')
            total_commission = Decimal('0.00')

            # Получаем данные по каждому инфлюенсеру
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context=serializer_context)
                result = self.get_paginated_response(serializer.data)
                data = result.data
            else:
                serializer = self.get_serializer(queryset, many=True, context=serializer_context)
                data = serializer.data

            # Подсчитываем общие суммы
            for item in serializer.data:
                total_revenue += Decimal(str(item['revenue']))
                total_commission += Decimal(str(item['commission']))

            # Формируем итоговый ответ
            response_data = {
                'total_revenue': float(total_revenue),
                'total_commission': float(total_commission),
                'lessors_count': queryset.count(),
            }

            # Если есть пагинация
            if isinstance(data, dict):
                data.update(response_data)
                return Response(data)

            # Если нет пагинации
            return Response({
                **response_data,
                'results': data
            })
        except Exception as e:
            raise


@extend_schema(summary="Отчеты. Франшизы", description="Отчеты. Франшизы.")
class FranchiseReportView(ListAPIView):
    serializer_class = FranchiseReportSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = FranchiseReportFilter
    permission_classes = [IsAdminRole]

    def get_queryset(self):
        return Franchise.objects.all()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            result = self.get_paginated_response(serializer.data)
            data = result.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        total_completed_amount = sum(item['completed_orders_amount'] for item in serializer.data)
        total_lessors_commission = sum(item['lessors_commission'] for item in serializer.data)
        total_canceled_amount = sum(item['canceled_orders_amount'] for item in serializer.data)
        total_franchise_commission = sum(item['franchise_commission_amount'] for item in serializer.data)
        total_canceled_count = sum(item['canceled_orders_count'] for item in serializer.data)

        avg_commission = queryset.aggregate(
            avg=Avg('commission')
        )['avg'] or 0

        response_data = {
            'total_completed_amount': total_completed_amount,
            'total_lessors_commission': total_lessors_commission,
            'avg_lessors_commission': float(avg_commission),
            'total_canceled_count': total_canceled_count,
            'total_canceled_amount': total_canceled_amount,
            'total_franchise_commission': total_franchise_commission
        }

        if isinstance(data, dict):
            data.update(response_data)
            return Response(data)

        return Response({
            **response_data,
            'results': data
        })

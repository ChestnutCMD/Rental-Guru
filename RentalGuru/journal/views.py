from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from chat.models import Trip
from franchise.models import Franchise
from journal.filters import TripFilter
from journal.permissions import IsAdminManagerOrFranchiseOwner
from journal.serializers import TripSerializer
from vehicle.models import Vehicle


class CustomLimitOffsetPagination(LimitOffsetPagination):
    def get_paginated_response(self, data):
        return Response({
            'count': self.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


@extend_schema(summary="Журнал аренды", description="Журнал аренды")
class TripByFranchiseView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminManagerOrFranchiseOwner]
    serializer_class = TripSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TripFilter
    pagination_class = CustomLimitOffsetPagination

    def get_queryset(self):
        franchise_id = self.kwargs.get('franchise_id')
        try:
            franchise = Franchise.objects.get(id=franchise_id)
        except Franchise.DoesNotExist:
            return Trip.objects.none()

        vehicles = Vehicle.objects.filter(
            Q(owner__lessor__franchise=franchise) | Q(owner=franchise.director)
        )

        trips = Trip.objects.filter(object_id__in=vehicles.values_list('id', flat=True)) \
            .select_related('organizer', 'content_type') \
            .prefetch_related('object_id__owner')
        return trips

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        count_query_params = request.query_params.copy()

        if 'type' in count_query_params:
            del count_query_params['type']

        count_filter = self.filterset_class(
            data=count_query_params,
            queryset=queryset,
            request=request
        )
        filtered_queryset_for_counts = count_filter.qs

        type_counts = filtered_queryset_for_counts.values('content_type__model').annotate(
            count=Count('content_type__model')
        )

        counts_dict = {
            item['content_type__model']: item['count']
            for item in type_counts
        }

        counts = {
            'auto': counts_dict.get('auto', 0),
            'bike': counts_dict.get('bike', 0),
            'ship': counts_dict.get('ship', 0),
            'helicopter': counts_dict.get('helicopter', 0),
            'specialtechnic': counts_dict.get('specialtechnic', 0)
        }

        filtered_queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)

            response_data = {
                'counts': counts,
                'data': serializer.data
            }

            return self.get_paginated_response(response_data)

        serializer = self.get_serializer(filtered_queryset, many=True)
        return Response({
            'counts': counts,
            'data': serializer.data
        })
from collections import Counter

from django.db.models import Q
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


@extend_schema(summary="Журнал аренды", description="Журнал аренды")
class TripByFranchiseView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminManagerOrFranchiseOwner]
    serializer_class = TripSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TripFilter
    pagination_class = LimitOffsetPagination

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
        queryset = self.filter_queryset(self.get_queryset())

        type_counts = Counter(queryset.values_list('content_type__model', flat=True))

        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(page, type_counts)

        serializer = self.get_serializer(queryset, many=True)
        return Response({"counts": type_counts, "data": serializer.data})

    def get_paginated_response(self, data, type_counts):
        response = self.paginator.get_paginated_response(data)
        response.data["results"] = {
            "counts": type_counts,
            "data": response.data.pop("results"),
        }
        return response

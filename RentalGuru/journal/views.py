from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

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

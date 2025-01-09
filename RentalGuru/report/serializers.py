from app.models import Lessor
from chat.models import Trip

from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum, Max
from django.contrib.contenttypes.models import ContentType

from vehicle.models import Vehicle


class LessorReportSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    last_name = serializers.CharField(source='user.last_name')
    first_name = serializers.CharField(source='user.first_name')
    avatar = serializers.ImageField(source='user.avatar')
    telephone = serializers.CharField(source='user.telephone')
    total_revenue = serializers.SerializerMethodField()
    commission_amount = serializers.SerializerMethodField()
    last_rent_date = serializers.SerializerMethodField()

    class Meta:
        model = Lessor
        fields = ['id', 'last_name', 'first_name', 'avatar', 'telephone',
                  'total_revenue', 'commission_amount', 'last_rent_date']

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

    def get_total_revenue(self, obj):
        trips = self.get_trips_for_lessor(obj)
        return trips.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    def get_commission_amount(self, obj):
        total_revenue = self.get_total_revenue(obj)
        return (total_revenue * obj.commission) / 100

    def get_last_rent_date(self, obj):
        trips = self.get_trips_for_lessor(obj)
        return trips.aggregate(last_date=Max('end_date'))['last_date']

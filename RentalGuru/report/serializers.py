from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum, Max

from app.models import Lessor
from chat.models import Trip


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

    def get_total_revenue(self, obj):
        return Trip.objects.filter(
            vehicle__owner=obj.user,
            status='finished'
        ).aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    def get_commission_amount(self, obj):
        total_revenue = self.get_total_revenue(obj)
        return (total_revenue * obj.commission) / 100

    def get_last_rent_date(self, obj):
        last_trip = Trip.objects.filter(
            vehicle__owner=obj.user,
            status='finished'
        ).aggregate(last_date=Max('end_date'))['last_date']
        return last_trip

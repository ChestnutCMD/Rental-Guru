from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum, Max, Q

from app.models import Lessor
from chat.models import Trip
from influencer.models import Influencer
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

        content_type_query = Q()
        for vehicle_type in vehicle_types:
            content_type = ContentType.objects.get(model=vehicle_type)
            vehicles = Vehicle.objects.filter(
                owner=lessor.user,
                polymorphic_ctype=content_type
            ).values_list('id', flat=True)

            if vehicles:
                content_type_query |= Q(
                    content_type=content_type,
                    object_id__in=vehicles
                )

        return Trip.objects.filter(content_type_query)

    def get_total_revenue(self, obj):
        trips = self.get_trips_for_lessor(obj)
        return trips.aggregate(total=Sum('total_cost'))['total'] or Decimal('0.00')

    def get_commission_amount(self, obj):
        total_revenue = self.get_total_revenue(obj)
        return (total_revenue * obj.commission) / 100

    def get_last_rent_date(self, obj):
        trips = self.get_trips_for_lessor(obj)
        return trips.aggregate(last_date=Max('end_date'))['last_date']


class InfluencerReportSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    last_name = serializers.CharField(source='user.last_name')
    first_name = serializers.CharField(source='user.first_name')
    avatar = serializers.ImageField(source='user.avatar')
    telephone = serializers.CharField(source='user.telephone')
    revenue = serializers.SerializerMethodField()
    commission = serializers.SerializerMethodField()
    last_rent_date = serializers.SerializerMethodField()

    class Meta:
        model = Influencer
        fields = ['id', 'last_name', 'first_name', 'avatar', 'telephone',
                  'revenue', 'commission', 'last_rent_date']

    def get_revenue(self, obj):
        filters = {}
        context = self.context
        period = context.get('period')
        city = context.get('city')

        if period:
            today = timezone.now().date()
            if period == 'day':
                start_date = today
            elif period == 'week':
                start_date = today - timedelta(days=7)
            elif period == 'month':
                start_date = today - timedelta(days=30)
            elif period == 'quarter':
                start_date = today - timedelta(days=90)
            elif period == 'year':
                start_date = today - timedelta(days=365)

            filters['end_date__gte'] = start_date

        renter_users = obj.renters.values_list('user_id', flat=True)

        # Базовый запрос для поездок
        trips_query = Trip.objects.filter(
            organizer_id__in=renter_users,
            status='finished'
        )

        # Добавляем фильтр по городу
        if city:
            vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']
            city_query = Q()

            for vehicle_type in vehicle_types:
                content_type = ContentType.objects.get(model=vehicle_type)
                city_query |= Q(
                    content_type=content_type,
                    object_id__in=Vehicle.objects.filter(
                        city=city,
                        polymorphic_ctype=content_type
                    ).values_list('id', flat=True)
                )

            trips_query = trips_query.filter(city_query)

        # Применяем остальные фильтры и получаем сумму
        total_revenue = trips_query.filter(**filters).aggregate(
            total=Sum('total_cost')
        )['total']

        return float(total_revenue) if total_revenue else 0.00

    def get_commission(self, obj):
        revenue = self.get_revenue(obj)
        return (revenue * obj.commission) / 100

    def get_last_rent_date(self, obj):
        renter_users = obj.renters.values_list('user_id', flat=True)
        city = self.context.get('city')

        trips_query = Trip.objects.filter(
            organizer_id__in=renter_users,
            status='finished'
        )

        if city:
            vehicle_types = ['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']
            city_query = Q()

            for vehicle_type in vehicle_types:
                content_type = ContentType.objects.get(model=vehicle_type)
                city_query |= Q(
                    content_type=content_type,
                    object_id__in=Vehicle.objects.filter(
                        city=city,
                        polymorphic_ctype=content_type
                    ).values_list('id', flat=True)
                )

            trips_query = trips_query.filter(city_query)

        last_date = trips_query.aggregate(
            last_date=Max('end_date')
        )['last_date']

        return last_date

from django.db import models
from rest_framework import serializers

from app.models import User, Lessor
from chat.models import RequestRent
from franchise.models import Franchise, VehiclePark, Category, RequestFranchise, City
from franchise.serializers.vehicle_park import VehicleParkRetrieveSerializer, VehicleSerializer
from vehicle.models import Vehicle


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id']


class FranchiseListSerializer(serializers.ModelSerializer):
    director = serializers.StringRelatedField()
    categories = CategorySerializer(many=True)

    class Meta:
        model = Franchise
        fields = [
            'id',
            'director',
            'name',
            'unn',
            'date_register',
            'telephone',
            'email',
            'country',
            'city',
            'commission',
            'total_vehicles',
            'categories'
        ]


class FranchiseRetrieveSerializer(serializers.ModelSerializer):
    vehicle_parks = serializers.SerializerMethodField()
    vehicles = serializers.SerializerMethodField()

    class Meta:
        model = Franchise
        fields = [
            'telephone',
            'country',
            'city',
            'vehicle_parks',
            'vehicles',
            'total_vehicles'
        ]

    def get_vehicle_parks(self, obj):
        # Получаем парки у арендодателей, связанных с франшизой, или владельцем которых является директор франшизы
        vehicle_parks = VehiclePark.objects.filter(
            models.Q(owner__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleParkRetrieveSerializer(vehicle_parks, many=True).data

    def get_vehicles(self, obj):
        # Получаем транспорт у арендодателей, связанных с франшизой, или владельцем которого является директор франшизы
        vehicles = Vehicle.objects.filter(
            models.Q(owner__lessor__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleSerializer(vehicles, many=True).data


class FranchiseCreateSerializer(serializers.ModelSerializer):
    director = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Franchise
        fields = [
            'name',
            'director',
            'unn',
            'telephone',
            'country',
            'city'
        ]


class VehicleParkUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePark
        fields = ['id']


class VehicleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id']


class FranchiseUpdateSerializer(serializers.ModelSerializer):
    vehicle_parks = VehicleParkRetrieveSerializer(many=True, read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True)

    class Meta:
        model = Franchise
        fields = [
            'id',
            'name',
            'director',
            'unn',
            'telephone',
            'country',
            'city',
            'vehicle_parks',
            'vehicles'
        ]

    def get_vehicle_parks(self, obj):
        vehicle_parks = VehiclePark.objects.filter(
            models.Q(lessor__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleParkRetrieveSerializer(vehicle_parks, many=True).data

    def get_vehicles(self, obj):
        vehicles = Vehicle.objects.filter(
            models.Q(owner__lessor__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleSerializer(vehicles, many=True).data

    def update(self, instance, validated_data):
        # Обновляем простые поля
        instance.name = validated_data.get('name', instance.name)
        instance.director = validated_data.get('director', instance.director)
        instance.unn = validated_data.get('unn', instance.unn)
        instance.telephone = validated_data.get('telephone', instance.telephone)
        instance.country = validated_data.get('country', instance.country)
        instance.city = validated_data.get('city', instance.city)

        instance.save()
        return instance


class FranchiseDeleteSerializer(serializers.Serializer):
    pass


class RequestRentSerializer(serializers.ModelSerializer):
    organizer = serializers.StringRelatedField()
    type = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = RequestRent
        fields = ['id', 'organizer', 'type', 'status', 'object', 'start_date', 'end_date', 'total_cost']

    def get_type(self, obj):
        return obj.content_type.model

    def get_object(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle) if vehicle else None

    def get_queryset(self):
        franchise = self.context['franchise']
        return RequestRent.objects.filter(
            models.Q(vehicle__owner__lessor__franchise=franchise) | models.Q(vehicle__owner=franchise.director)
        )


class LessorSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Lessor
        fields = [
            'id',
            'user',
            'super_host',
            'count_trip',
            'average_response_time',
            'franchise'
        ]


class FranchiseStatisticsSerializer(serializers.Serializer):
    total_vehicles = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_margin = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_completed_orders = serializers.IntegerField()
    total_cancelled_orders = serializers.IntegerField()
    active_users_count = serializers.IntegerField()


class RequestFranchiseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestFranchise
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    finished_trips_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = City
        fields = ['id', 'title', 'finished_trips_count']
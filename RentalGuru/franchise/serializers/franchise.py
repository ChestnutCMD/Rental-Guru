from rest_framework import serializers

from RentalGuru import settings
from app.models import User
from franchise.models import Franchise, VehiclePark, Category
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
    vehicle_parks = VehicleParkRetrieveSerializer(many=True, read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True)

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

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Форматирование данных автопарков
        vehicle_parks = representation.pop('vehicle_parks', [])
        formatted_vehicle_parks = []
        for park in vehicle_parks:
            park_data = VehicleParkRetrieveSerializer(instance=park).data
            formatted_vehicle_parks.append(park_data)

        # Форматирование данных транспортных средств
        vehicles = representation.pop('vehicles', [])
        formatted_vehicles = []
        for vehicle in vehicles:
            vehicle_data = VehicleSerializer(instance=vehicle).data
            formatted_vehicles.append(vehicle_data)

        # Объединение данных в один результат
        result = {
            'telephone': representation.get('telephone'),
            'country': representation.get('country'),
            'city': representation.get('city'),
            'vehicle_parks': formatted_vehicle_parks,
            'vehicles': formatted_vehicles,
            'total_vehicles': representation.get('total_vehicles')
        }

        return result


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

    def update(self, instance, validated_data):
        # Обновляем простые поля
        instance.name = validated_data.get('name', instance.name)
        instance.director = validated_data.get('director', instance.director)
        instance.unn = validated_data.get('unn', instance.unn)
        instance.telephone = validated_data.get('telephone', instance.telephone)
        instance.country = validated_data.get('country', instance.country)
        instance.city = validated_data.get('city', instance.city)

        # Обработка связанных автопарков (VehiclePark)
        vehicle_parks_data = validated_data.get('vehicle_parks', [])
        new_vehicle_park_ids = [park.get('id') for park in vehicle_parks_data if park.get('id') is not None]

        # Получаем новые автопарки для добавления
        new_vehicle_parks = VehiclePark.objects.filter(id__in=new_vehicle_park_ids)

        # Добавляем новые автопарки к франшизе
        instance.vehicle_parks.add(*new_vehicle_parks)

        # Обработка связанных транспортных средств (Vehicles)
        vehicles_data = validated_data.get('vehicles', [])
        vehicle_ids = [vehicle.get('id') for vehicle in vehicles_data if vehicle.get('id') is not None]

        vehicles = Vehicle.objects.filter(id__in=vehicle_ids)
        for vehicle in vehicles:
            vehicle.franchise = instance
            vehicle.save()

        instance.save()
        return instance


class FranchiseDeleteSerializer(serializers.Serializer):
    pass

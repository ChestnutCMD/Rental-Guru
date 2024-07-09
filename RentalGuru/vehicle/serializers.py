from .models import Auto, Bike, Ship, Helicopter, SpecialTechnic

from rest_framework import serializers
from .models import VehicleBrand, VehicleModel


class VehicleBrandSerializer(serializers.ModelSerializer):

    class Meta:
        model = VehicleBrand
        fields = '__all__'


class VehicleModelSerializer(serializers.ModelSerializer):
    brand = serializers.PrimaryKeyRelatedField(
        queryset=VehicleBrand.objects.all(),
        required=True
    )

    class Meta:
        model = VehicleModel
        fields = ['name', 'brand']

    def create(self, validated_data):
        brand = validated_data['brand']
        name = validated_data['name']
        vehicle_model = VehicleModel.objects.create(brand=brand, name=name)
        return vehicle_model

    def update(self, instance, validated_data):
        instance.brand = validated_data.get('brand', instance.brand)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance


class BaseVehicleSerializer(serializers.ModelSerializer):
    class Meta:
        # model будет определен в наследуемых классах
        fields = '__all__'
        read_only_fields = ['owner']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['owner'] = request.user
        if 'ratings' not in validated_data:
            validated_data['ratings'] = 0  # Установить значение по умолчанию
        return super().create(validated_data)


class AutoSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = Auto


class BikeSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = Bike


class ShipSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = Ship


class HelicopterSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = Helicopter


class SpecialTechnicSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = SpecialTechnic

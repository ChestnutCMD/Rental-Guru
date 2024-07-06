from rest_framework import serializers
from .models import Vehicle, VehicleType, VehicleBrand, VehicleModel


class VehicleTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleType
        fields = '__all__'


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = '__all__'


class VehicleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = '__all__'


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

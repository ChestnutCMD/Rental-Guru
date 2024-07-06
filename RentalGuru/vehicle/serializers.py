from rest_framework import serializers
from .models import VehicleBrand, VehicleModel, Auto, Bike, Ship, Helicopter, SpecialTechnic


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = '__all__'


class VehicleModelSerializer(serializers.ModelSerializer):
    brand = VehicleBrandSerializer()

    class Meta:
        model = VehicleModel
        fields = '__all__'


class AutoSerializer(serializers.ModelSerializer):
    model = VehicleModelSerializer()

    class Meta:
        model = Auto
        fields = '__all__'


class BikeSerializer(serializers.ModelSerializer):
    model = VehicleModelSerializer()

    class Meta:
        model = Bike
        fields = '__all__'


class ShipSerializer(serializers.ModelSerializer):
    model = VehicleModelSerializer()

    class Meta:
        model = Ship
        fields = '__all__'


class HelicopterSerializer(serializers.ModelSerializer):
    model = VehicleModelSerializer()

    class Meta:
        model = Helicopter
        fields = '__all__'


class SpecialTechnicSerializer(serializers.ModelSerializer):
    model = VehicleModelSerializer()

    class Meta:
        model = SpecialTechnic
        fields = '__all__'

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from vehicle.models import Bike, VehicleFeaturesFunctions, BikeFeaturesAdditionally, BikeTransmission, VehicleClass
from vehicle.serializers.base import BaseVehicleGetSerializer, BaseVehicleListSerializer, BaseVehicleCreateSerializer, \
    BaseVehicleUpdateSerializer, VehicleClassSerializer


class BikeTransmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BikeTransmission
        fields = '__all__'


class BikeCreateSerializer(BaseVehicleCreateSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=BikeFeaturesAdditionally.objects.all())
    transmission = serializers.PrimaryKeyRelatedField(queryset=BikeTransmission.objects.all())
    vehicle_class = serializers.PrimaryKeyRelatedField(queryset=VehicleClass.objects.all())

    class Meta(BaseVehicleCreateSerializer.Meta):
        model = Bike

    def create(self, validated_data):
        features_functions_data = validated_data.pop('features_functions', [])
        features_additionally_data = validated_data.pop('features_additionally', [])

        vehicle = super().create(validated_data)

        vehicle.features_functions.set(features_functions_data)
        vehicle.features_additionally.set(features_additionally_data)

        return vehicle


class BikeUpdateSerializer(BaseVehicleUpdateSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=BikeFeaturesAdditionally.objects.all())
    transmission = serializers.PrimaryKeyRelatedField(queryset=BikeTransmission.objects.all())
    vehicle_class = serializers.PrimaryKeyRelatedField(queryset=VehicleClass.objects.all())

    class Meta(BaseVehicleUpdateSerializer.Meta):
        model = Bike


class BikeFeaturesAdditionallySerializer(serializers.ModelSerializer):
    class Meta:
        model = BikeFeaturesAdditionally
        fields = '__all__'


class BikeGetSerializer(BaseVehicleGetSerializer):
    features_functions = serializers.SerializerMethodField()
    features_additionally = serializers.SerializerMethodField()
    transmission = BikeTransmissionSerializer()
    vehicle_class = VehicleClassSerializer()

    class Meta(BaseVehicleGetSerializer.Meta):
        model = Bike

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_functions(self, obj):
        return [feature.name for feature in obj.features_functions.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_additionally(self, obj):
        return [feature.name for feature in obj.features_additionally.all()]


class BikeListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = Bike

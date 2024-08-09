from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from vehicle.models import Bike, VehicleFeaturesFunctions, BikeFeaturesAdditionally
from vehicle.serializers.base import BaseVehicleGetSerializer, BaseVehicleListSerializer, BaseVehicleCreateSerializer, \
    BaseVehicleUpdateSerializer


class BikeCreateSerializer(BaseVehicleCreateSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=BikeFeaturesAdditionally.objects.all())

    class Meta(BaseVehicleCreateSerializer.Meta):
        model = Bike


class BikeUpdateSerializer(BaseVehicleUpdateSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=BikeFeaturesAdditionally.objects.all())

    class Meta(BaseVehicleUpdateSerializer.Meta):
        model = Bike


class BikeFeaturesAdditionallySerializer(serializers.ModelSerializer):
    class Meta:
        model = BikeFeaturesAdditionally
        fields = ['name']


class BikeGetSerializer(BaseVehicleGetSerializer):
    features_functions = serializers.SerializerMethodField()
    features_additionally = serializers.SerializerMethodField()

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

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from vehicle.models import VehicleFeaturesFunctions, ShipFeaturesAdditionally, FeaturesEquipment, Ship
from vehicle.serializers.base import BaseVehicleGetSerializer, BaseVehicleListSerializer, \
    BaseVehicleCreateSerializer, BaseVehicleUpdateSerializer


class ShipCreateSerializer(BaseVehicleCreateSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=ShipFeaturesAdditionally.objects.all())
    features_equipment = serializers.PrimaryKeyRelatedField(many=True, queryset=FeaturesEquipment.objects.all())

    class Meta(BaseVehicleCreateSerializer.Meta):
        model = Ship


class ShipUpdateSerializer(BaseVehicleUpdateSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=ShipFeaturesAdditionally.objects.all())
    features_equipment = serializers.PrimaryKeyRelatedField(many=True, queryset=FeaturesEquipment.objects.all())

    class Meta(BaseVehicleUpdateSerializer.Meta):
        model = Ship


class ShipFeaturesAdditionallySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipFeaturesAdditionally
        fields = ['name']


class FeaturesEquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturesEquipment
        fields = ['name']


class ShipGetSerializer(BaseVehicleGetSerializer):
    features_functions = serializers.SerializerMethodField()
    features_additionally = serializers.SerializerMethodField()
    features_equipment = serializers.SerializerMethodField()

    class Meta(BaseVehicleGetSerializer.Meta):
        model = Ship

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_functions(self, obj):
        return [feature.name for feature in obj.features_functions.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_additionally(self, obj):
        return [feature.name for feature in obj.features_additionally.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_equipment(self, obj):
        return [feature.name for feature in obj.features_equipment.all()]


class ShipListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = Ship

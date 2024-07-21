from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .base import BaseVehicleSerializer, BaseVehicleGetSerializer, VehicleFeaturesFunctionsSerializer, \
    BaseVehicleListSerializer
from ..models import FeaturesForChildren, VehicleFeaturesFunctions, AutoFeaturesAdditionally, Auto


class AutoSerializer(BaseVehicleSerializer):
    features_for_children = serializers.PrimaryKeyRelatedField(many=True, queryset=FeaturesForChildren.objects.all())
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=AutoFeaturesAdditionally.objects.all())

    class Meta(BaseVehicleSerializer.Meta):
        model = Auto


class FeaturesForChildrenSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeaturesForChildren
        fields = ['name']


class AutoFeaturesAdditionallySerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoFeaturesAdditionally
        fields = ['name']


class AutoGetSerializer(BaseVehicleGetSerializer):
    features_for_children = serializers.SerializerMethodField()
    features_functions = serializers.SerializerMethodField()
    features_additionally = serializers.SerializerMethodField()

    class Meta(BaseVehicleSerializer.Meta):
        model = Auto

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_for_children(self, obj):
        return [feature.name for feature in obj.features_for_children.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_functions(self, obj):
        return [feature.name for feature in obj.features_functions.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_features_additionally(self, obj):
        return [feature.name for feature in obj.features_additionally.all()]


class AutoListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = Auto

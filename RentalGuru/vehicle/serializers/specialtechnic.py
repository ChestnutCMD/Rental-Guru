from vehicle.models import SpecialTechnic
from vehicle.serializers.base import BaseVehicleGetSerializer, BaseVehicleListSerializer, BaseVehicleCreateSerializer, BaseVehicleUpdateSerializer


class SpecialTechnicCreateSerializer(BaseVehicleCreateSerializer):
    class Meta(BaseVehicleCreateSerializer.Meta):
        model = SpecialTechnic


class SpecialTechnicUpdateSerializer(BaseVehicleUpdateSerializer):
    class Meta(BaseVehicleUpdateSerializer.Meta):
        model = SpecialTechnic


class SpecialTechnicGetSerializer(BaseVehicleGetSerializer):
    class Meta(BaseVehicleGetSerializer.Meta):
        model = SpecialTechnic


class SpecialTechnicListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = SpecialTechnic

from vehicle.models import SpecialTechnic
from vehicle.serializers.base import BaseVehicleSerializer, BaseVehicleGetSerializer, BaseVehicleListSerializer


class SpecialTechnicSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = SpecialTechnic


class SpecialTechnicGetSerializer(BaseVehicleGetSerializer):
    class Meta(BaseVehicleGetSerializer.Meta):
        model = SpecialTechnic


class SpecialTechnicListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = SpecialTechnic

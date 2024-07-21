from vehicle.models import Helicopter
from vehicle.serializers.base import BaseVehicleSerializer, BaseVehicleGetSerializer, BaseVehicleListSerializer


class HelicopterSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = Helicopter


class HelicopterGetSerializer(BaseVehicleGetSerializer):
    class Meta(BaseVehicleGetSerializer.Meta):
        model = Helicopter


class HelicopterListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = Helicopter

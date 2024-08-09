from vehicle.models import Helicopter
from vehicle.serializers.base import BaseVehicleSerializer, BaseVehicleGetSerializer, BaseVehicleListSerializer, \
    BaseVehicleCreateSerializer, BaseVehicleUpdateSerializer


class HelicopterCreateSerializer(BaseVehicleCreateSerializer):
    class Meta(BaseVehicleCreateSerializer.Meta):
        model = Helicopter


class HelicopterUpdateSerializer(BaseVehicleUpdateSerializer):
    class Meta(BaseVehicleUpdateSerializer.Meta):
        model = Helicopter


class HelicopterGetSerializer(BaseVehicleGetSerializer):
    class Meta(BaseVehicleGetSerializer.Meta):
        model = Helicopter


class HelicopterListSerializer(BaseVehicleListSerializer):
    class Meta(BaseVehicleListSerializer.Meta):
        model = Helicopter

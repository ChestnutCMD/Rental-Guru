from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, generics
from .models import VehicleBrand, VehicleModel, Auto, Bike, Ship, Helicopter, SpecialTechnic
from .serializers import VehicleBrandSerializer, VehicleModelSerializer, AutoSerializer, BikeSerializer, ShipSerializer, \
    HelicopterSerializer, SpecialTechnicSerializer


@extend_schema(summary="Марка транспорта", description="Марка транспорта")
class VehicleBrandViewSet(viewsets.ModelViewSet):
    """ Марка транспорта """
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


@extend_schema(summary="Модель транспорта", description="Модель транспорта")
class VehicleModelViewSet(viewsets.ModelViewSet):
    """ Модель транспорта """
    queryset = VehicleModel.objects.all().select_related('brand')
    serializer_class = VehicleModelSerializer


@extend_schema(summary="Автомобиль", description="Автомобиль")
class AutoViewSet(viewsets.ModelViewSet):
    """ Автомобиль """
    queryset = Auto.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = AutoSerializer


@extend_schema(summary="Мотоцикл", description="Мотоцикл")
class BikeViewSet(viewsets.ModelViewSet):
    """ Мотоцикл """
    queryset = Bike.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = BikeSerializer


@extend_schema(summary="Судно", description="Судно")
class ShipViewSet(viewsets.ModelViewSet):
    """ Судно """
    queryset = Ship.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = ShipSerializer


@extend_schema(summary="Вертолет", description="Вертолет")
class HelicopterViewSet(viewsets.ModelViewSet):
    """ Вертолет """
    queryset = Helicopter.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = HelicopterSerializer


@extend_schema(summary="Спецтехника", description="Спецтехника")
class SpecialTechnicViewSet(viewsets.ModelViewSet):
    """ Спецтехника """
    queryset = SpecialTechnic.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = SpecialTechnicSerializer

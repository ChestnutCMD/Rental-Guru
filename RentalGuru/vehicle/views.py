from rest_framework import viewsets, generics
from .models import VehicleBrand, VehicleModel, Auto, Bike, Ship, Helicopter, SpecialTechnic
from .serializers import VehicleBrandSerializer, VehicleModelSerializer, AutoSerializer, BikeSerializer, ShipSerializer, \
    HelicopterSerializer, SpecialTechnicSerializer


class VehicleBrandViewSet(viewsets.ModelViewSet):
    """ Марка транспорта """
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


class VehicleModelViewSet(viewsets.ModelViewSet):
    """ Модель транспорта """
    queryset = VehicleModel.objects.all().select_related('brand')
    serializer_class = VehicleModelSerializer


class AutoViewSet(viewsets.ModelViewSet):
    """ Автомобиль """
    queryset = Auto.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = AutoSerializer


class BikeViewSet(viewsets.ModelViewSet):
    """ Мотоцикл """
    queryset = Bike.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = BikeSerializer


class ShipViewSet(viewsets.ModelViewSet):
    """ Судно """
    queryset = Ship.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = ShipSerializer


class HelicopterViewSet(viewsets.ModelViewSet):
    """ Вертолет """
    queryset = Helicopter.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = HelicopterSerializer


class SpecialTechnicViewSet(viewsets.ModelViewSet):
    """ Спецтехника """
    queryset = SpecialTechnic.objects.all().select_related('owner', 'brand', 'model')
    serializer_class = SpecialTechnicSerializer

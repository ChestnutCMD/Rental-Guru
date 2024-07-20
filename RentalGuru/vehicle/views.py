from rest_framework import viewsets
from drf_spectacular.utils import extend_schema
from .models import VehicleBrand, VehicleModel, Auto, Bike, Ship, Helicopter, SpecialTechnic
from .serializers import VehicleBrandSerializer, VehicleModelSerializer, AutoSerializer, BikeSerializer, ShipSerializer, HelicopterSerializer, SpecialTechnicSerializer


@extend_schema(summary="Марка транспорта", description="Марка транспорта")
class VehicleBrandViewSet(viewsets.ModelViewSet):
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


@extend_schema(summary="Модель транспорта", description="Модель транспорта")
class VehicleModelViewSet(viewsets.ModelViewSet):
    queryset = VehicleModel.objects.all().select_related('brand')
    serializer_class = VehicleModelSerializer


@extend_schema(summary="Автомобиль", description="Автомобиль")
class AutoViewSet(viewsets.ModelViewSet):
    queryset = (Auto.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'features_for_children', 'features_functions',
                                 'features_additionally', 'availabilities', 'documents', 'rent_prices'))
    serializer_class = AutoSerializer


@extend_schema(summary="Мотоцикл", description="Мотоцикл")
class BikeViewSet(viewsets.ModelViewSet):
    queryset = (Bike.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'features_functions', 'features_additionally', 'availabilities',
                                 'documents', 'rent_prices'))
    serializer_class = BikeSerializer


@extend_schema(summary="Судно", description="Судно")
class ShipViewSet(viewsets.ModelViewSet):
    queryset = (Ship.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'features_functions', 'features_additionally', 'features_equipment',
                                 'availabilities', 'documents', 'rent_prices'))
    serializer_class = ShipSerializer


@extend_schema(summary="Вертолет", description="Вертолет")
class HelicopterViewSet(viewsets.ModelViewSet):
    queryset = (Helicopter.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'availabilities', 'documents', 'rent_prices'))
    serializer_class = HelicopterSerializer


@extend_schema(summary="Спецтехника", description="Спецтехника")
class SpecialTechnicViewSet(viewsets.ModelViewSet):
    queryset = (SpecialTechnic.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'availabilities', 'documents', 'rent_prices'))
    serializer_class = SpecialTechnicSerializer

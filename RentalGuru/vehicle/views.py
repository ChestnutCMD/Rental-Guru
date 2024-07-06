from rest_framework import generics
from .models import Vehicle, VehicleType, VehicleBrand, VehicleModel
from .serializers import VehicleSerializer, VehicleTypeSerializer, VehicleBrandSerializer, VehicleModelSerializer


class VehicleListCreateAPIView(generics.ListCreateAPIView):
    """Получение списка транспорта и добавление транспорта"""
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class VehicleDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Получение, обновление, удаление транспорта по ID"""
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class VehicleTypeListCreateAPIView(generics.ListCreateAPIView):
    """Получение списка типов транспорта(авто, вертолет, спецтехника и т.д.) и добавление типа транспорта"""
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer


class VehicleTypeDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Получение, обновление, удаление типа транспорта(авто, вертолет, спецтехника и т.д.) по ID"""
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer


class VehicleBrandListCreateAPIView(generics.ListCreateAPIView):
    """Получение списка маркок транспорта() и добавление марки транспорта"""
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


class VehicleBrandDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Получение, обновление, удаление марки транспорта по ID"""
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


class VehicleModelListCreateAPIView(generics.ListCreateAPIView):
    """Получение списка и добавление моделей транспорта"""
    queryset = VehicleModel.objects.all()
    serializer_class = VehicleModelSerializer


class VehicleModelDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Получение, обновление, удаление модели транспорта по ID"""
    queryset = VehicleModel.objects.all()
    serializer_class = VehicleModelSerializer

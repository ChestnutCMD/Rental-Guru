from rest_framework import generics
from .models import Vehicle, VehicleType, VehicleBrand, VehicleModel
from .serializers import VehicleSerializer, VehicleTypeSerializer, VehicleBrandSerializer, VehicleModelSerializer


class VehicleListCreateAPIView(generics.ListCreateAPIView):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class VehicleDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vehicle.objects.all()
    serializer_class = VehicleSerializer


class VehicleTypeListCreateAPIView(generics.ListCreateAPIView):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer


class VehicleTypeDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VehicleType.objects.all()
    serializer_class = VehicleTypeSerializer


class VehicleBrandListCreateAPIView(generics.ListCreateAPIView):
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


class VehicleBrandDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer


class VehicleModelListCreateAPIView(generics.ListCreateAPIView):
    queryset = VehicleModel.objects.all()
    serializer_class = VehicleModelSerializer


class VehicleModelDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = VehicleModel.objects.all()
    serializer_class = VehicleModelSerializer

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Trip, Chat, RequestRent
from vehicle.models import Vehicle
from .models import VehiclePark, Franchise
from .permissions import IsOwnerOrAdmin, IsOwnerOrAdminForGet
from franchise.serializers.vehicle_park import VehicleParkRetrieveSerializer, VehicleParkListSerializer, \
    VehicleParkCreateSerializer, VehicleParkUpdateSerializer, ChatSerializer, RequestRentSerializer
from .serializers.franchise import FranchiseListSerializer, FranchiseRetrieveSerializer, \
    FranchiseCreateSerializer, FranchiseUpdateSerializer, FranchiseDeleteSerializer


class VehicleParkViewSet(viewsets.ModelViewSet):
    queryset = VehiclePark.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return VehicleParkRetrieveSerializer
        elif self.action == 'list':
            return VehicleParkListSerializer
        elif self.action == 'create':
            return VehicleParkCreateSerializer
        elif self.action in ['partial_update', 'update']:
            return VehicleParkUpdateSerializer
        return VehicleParkListSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return [IsAuthenticated()]

    def perform_destroy(self, instance):
        instance.delete()

    def perform_update(self, serializer):
        serializer.save()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class RequestsByParkView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdminForGet]

    def get(self, request, park_id, format=None):
        try:
            vehicles = Vehicle.objects.filter(vehicle_park_id=park_id)
        except VehiclePark.DoesNotExist:
            return Response({'detail': 'Vehicle park not found.'}, status=status.HTTP_404_NOT_FOUND)

        requests = (RequestRent.objects.filter(object_id__in=vehicles.values_list('id', flat=True))
                    .select_related('content_type'))

        # Используем обновленный сериализатор
        serialized_requests = RequestRentSerializer(requests, many=True).data

        count_dict = {
            "auto": 0,
            "bike": 0,
            "ship": 0,
            "helicopter": 0,
            "special_technic": 0
        }

        # Заполняем словарь с подсчетом
        for request in serialized_requests:
            content_type_name = request['type']
            if content_type_name in count_dict:
                count_dict[content_type_name] += 1

        data = {
            "auto": [],
            "bike": [],
            "ship": [],
            "helicopter": [],
            "special_technic": []
        }

        # Заполняем данные
        for request in serialized_requests:
            content_type_name = request['type']
            if content_type_name == "auto":
                data["auto"].append(request)
            elif content_type_name == "bike":
                data["bike"].append(request)
            elif content_type_name == "ship":
                data["ship"].append(request)
            elif content_type_name == "helicopter":
                data["helicopter"].append(request)
            elif content_type_name == "specialtechnic":
                data["special_technic"].append(request)

        result = {
            "counts": count_dict,
            "data": data
        }

        return Response(result, status=status.HTTP_200_OK)


class ChatsByParkView(APIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdminForGet]

    def get(self, request, park_id, format=None):
        try:
            vehicles = (Vehicle.objects.filter(vehicle_park_id=park_id)
                        .select_related('owner', 'brand', 'model')
                        .prefetch_related('trips'))
        except VehiclePark.DoesNotExist:
            return Response({'detail': 'Vehicle park not found.'}, status=status.HTTP_404_NOT_FOUND)

        trips = Trip.objects.filter(object_id__in=vehicles.values_list('id', flat=True))
        chats = Chat.objects.filter(trip__in=trips)

        serializer = ChatSerializer(chats, many=True)
        return Response(serializer.data)


class FranchiseViewSet(viewsets.ModelViewSet):
    queryset = Franchise.objects.all()
    permission_classes = [IsAuthenticated, IsOwnerOrAdminForGet]

    def get_serializer_class(self):
        if self.action == 'list':
            return FranchiseListSerializer
        elif self.action == 'retrieve':
            return FranchiseRetrieveSerializer
        elif self.action == 'create':
            return FranchiseCreateSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return FranchiseUpdateSerializer
        elif self.action == 'destroy':
            return FranchiseDeleteSerializer
        return FranchiseListSerializer

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'results': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

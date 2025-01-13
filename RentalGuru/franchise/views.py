from django.db.models import Q
from django.db.models.expressions import RawSQL
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, generics
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Lessor, User
from chat.models import Trip, Chat, RequestRent
from vehicle.models import Vehicle
from .models import VehiclePark, Franchise, RequestFranchise, City
from .permissions import IsOwnerOrAdmin, IsOwnerOrAdminForGet, IsDirectorOrAdminForGet, IsAdminOrManager, IsAdmin
from franchise.serializers.vehicle_park import VehicleParkRetrieveSerializer, VehicleParkListSerializer, \
    VehicleParkCreateSerializer, VehicleParkUpdateSerializer, ChatSerializer, RequestRentSerializer, VehicleSerializer, \
    VehicleParkStatisticsSerializer
from .serializers.franchise import FranchiseListSerializer, FranchiseRetrieveSerializer, \
    FranchiseCreateSerializer, FranchiseUpdateSerializer, FranchiseDeleteSerializer, LessorSerializer, \
    FranchiseStatisticsSerializer, RequestFranchiseSerializer, CitySerializer


@extend_schema(summary="Автопарк CRUD", description="CRUD Автопарка")
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


@extend_schema(summary="Все заявки на аренду автопарка", description="Заявки на аренду автопарка")
class RequestsByParkView(APIView):
    permission_classes = [IsOwnerOrAdminForGet]

    def get(self, request, park_id, format=None):
        try:
            vehicles = Vehicle.objects.filter(vehicle_park_id=park_id)
        except VehiclePark.DoesNotExist:
            return Response({'detail': 'Vehicle park not found.'}, status=status.HTTP_404_NOT_FOUND)

        requests = (RequestRent.objects.filter(object_id__in=vehicles.values_list('id', flat=True))
                    .select_related('content_type'))

        serialized_requests = RequestRentSerializer(requests, many=True).data

        count_dict = {
            "auto": 0,
            "bike": 0,
            "ship": 0,
            "helicopter": 0,
            "special_technic": 0
        }

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


@extend_schema(summary="Все чаты автопарка", description="Чаты автопарка")
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


@extend_schema(summary="Франшиза CRUD", description="CRUD фарншизы")
class FranchiseViewSet(viewsets.ModelViewSet):
    queryset = Franchise.objects.all()
    permission_classes = [IsAuthenticated, IsDirectorOrAdminForGet]

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

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'results': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        franchise = serializer.save()
        return Response(FranchiseRetrieveSerializer(franchise).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(summary="Все заявки на аренду франшизы", description="Заявки на аренду франшизы")
class RequestsByFranchiseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, franchise_id, format=None):
        try:
            franchise = Franchise.objects.get(id=franchise_id)
        except Franchise.DoesNotExist:
            return Response({'detail': 'Franchise not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Получаем все транспорты, которые связаны с франшизой через арендодателя или владельца транспорта
        vehicles = Vehicle.objects.filter(
            Q(owner__lessor__franchise=franchise) | Q(owner=franchise.director)
        )

        # Фильтруем заявки на аренду по этим транспортам
        requests = RequestRent.objects.filter(object_id__in=vehicles.values_list('id', flat=True)).select_related('content_type')
        serialized_requests = RequestRentSerializer(requests, many=True).data

        # Считаем заявки по типам
        count_dict = {
            "auto": 0,
            "bike": 0,
            "ship": 0,
            "helicopter": 0,
            "special_technic": 0
        }

        for request in serialized_requests:
            content_type_name = request['type']
            if content_type_name in count_dict:
                count_dict[content_type_name] += 1

        # Группируем заявки по типам
        data = {
            "auto": [],
            "bike": [],
            "ship": [],
            "helicopter": [],
            "special_technic": []
        }

        for request in serialized_requests:
            content_type_name = request['type']
            if content_type_name in data:
                data[content_type_name].append(request)

        result = {
            "counts": count_dict,
            "data": data
        }

        return Response(result, status=status.HTTP_200_OK)


@extend_schema(summary="Все чаты франшизы", description="Чаты франшизы")
class ChatsByFranchiseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, franchise_id, format=None):
        try:
            franchise = Franchise.objects.get(id=franchise_id)
        except Franchise.DoesNotExist:
            return Response({'detail': 'Franchise not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Получаем все транспорты, которые связаны с франшизой через арендодателя или владельца транспорта
        vehicles = Vehicle.objects.filter(
            Q(owner__lessor__franchise=franchise) | Q(owner=franchise.director)
        )

        # Фильтруем поездки, связанные с этими транспортами
        trips = Trip.objects.filter(object_id__in=vehicles.values_list('id', flat=True))

        # Получаем чаты для этих поездок
        chats = Chat.objects.filter(trip__in=trips)
        serializer = ChatSerializer(chats, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(summary="Арендодатели франшизы", description="Арендодатели франшизы")
class LessorsByFranchiseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, franchise_id, format=None):
        try:
            franchise = Franchise.objects.get(id=franchise_id)
        except Franchise.DoesNotExist:
            return Response({'detail': 'Franchise not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Получаем всех арендодателей, связанных с этой франшизой
        lessors = Lessor.objects.filter(franchise=franchise)
        serializer = LessorSerializer(lessors, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(summary="Весь транспорт франшизы", description="Хуй знает зачем это надо, ведь есть /frinchize/{id}")
class VehiclesByFranchiseView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, franchise_id, format=None):
        try:
            franchise = Franchise.objects.get(id=franchise_id)
        except Franchise.DoesNotExist:
            return Response({'detail': 'Franchise not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Получаем все транспортные средства, связанные с франшизой через арендодателя или владельца (директора франшизы)
        vehicles = Vehicle.objects.filter(
            Q(owner__lessor__franchise=franchise) | Q(owner=franchise.director)
        )
        serializer = VehicleSerializer(vehicles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(summary="Статистика франшизы", description="Статистика франшизы")
@api_view(['GET'])
def franchise_statistics(request, franchise_id):
    try:
        franchise = Franchise.objects.get(pk=franchise_id)
    except Franchise.DoesNotExist:
        return Response({'detail': 'Franchise not found.'}, status=status.HTTP_404_NOT_FOUND)

    statistics = franchise.get_statistics()
    serializer = FranchiseStatisticsSerializer(statistics)

    return Response(serializer.data)


@extend_schema(summary="Статистика автопарка", description="Статистика автопарка")
@api_view(['GET'])
def vehicle_park_statistics(request, vehicle_park_id):
    try:
        vehicle_park = VehiclePark.objects.get(pk=vehicle_park_id)
    except VehiclePark.DoesNotExist:
        return Response({'detail': 'VehiclePark not found.'}, status=status.HTTP_404_NOT_FOUND)

    statistics = vehicle_park.get_statistics()
    serializer = VehicleParkStatisticsSerializer(statistics)

    return Response(serializer.data)


@extend_schema(summary="Заявка на создание франшизы", description="Заявку может отправить любой пользователь")
class RequestFranchiseCreateView(generics.CreateAPIView):
    queryset = RequestFranchise.objects.all()
    serializer_class = RequestFranchiseSerializer


@extend_schema(summary="Получение списка заявок на создание франшизы", description="Получение списка заявок на создание франшизы")
class RequestFranchiseListView(generics.ListAPIView):
    queryset = RequestFranchise.objects.all()
    serializer_class = RequestFranchiseSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]


@extend_schema(summary="Удаление заявки на создание франшизы", description="Удаление заявки на создание франшизы")
class RequestFranchiseDeleteView(generics.DestroyAPIView):
    queryset = RequestFranchise.objects.all()
    serializer_class = RequestFranchiseSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]


@extend_schema(summary="Список городов", description="Список городов")
class CityView(generics.ListAPIView):
    serializer_class = CitySerializer
    queryset = City.objects.annotate(
        finished_trips_count=RawSQL("""
                SELECT COUNT(DISTINCT t.id)
                FROM public.vehicle_vehicle v
                JOIN django_content_type ct ON v.polymorphic_ctype_id = ct.id
                JOIN public.chat_trip t ON t.object_id = v.id AND t.content_type_id = ct.id
                WHERE v.city_id = public.franchise_city.id AND t.status = 'finished'
            """, [])
    ).order_by('-finished_trips_count')



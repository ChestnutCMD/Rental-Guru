from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from RentalGuru import settings
from app.models import Lessor
from chat.models import Trip
from notification.models import Notification
from .filters import AutoFilter, BikeFilter, ShipFilter, HelicopterFilter, SpecialTechnicFilter
from .models import VehicleBrand, VehicleModel, Auto, Bike, Ship, Helicopter, SpecialTechnic, RatingUpdateLog, Vehicle, \
    VehicleFeaturesFunctions, AutoFeaturesAdditionally, BikeFeaturesAdditionally, ShipFeaturesAdditionally, \
    FeaturesForChildren, FeaturesEquipment, PaymentMethod, AutoFuelType, AutoTransmission, AutoBodyType, \
    BikeTransmission, VehicleClass
from .permission import IsAdminOrLessor, IsAdminOrReadOnly, IsAdminOrOwner
from .serializers.base import VehicleBrandSerializer, VehicleModelSerializer, VehicleFeaturesFunctionsSerializer, \
    PaymentMethodSerializer, VehicleClassSerializer
from .serializers.auto import AutoGetSerializer, AutoListSerializer, AutoCreateSerializer, \
    AutoUpdateSerializer, AutoFeaturesAdditionallySerializer, FeaturesForChildrenSerializer, AutoFuelTypeSerializer, \
    AutoTransmissionSerializer, AutoBodyTypeSerializer
from .serializers.bike import BikeGetSerializer, BikeListSerializer, BikeCreateSerializer, BikeUpdateSerializer, \
    BikeFeaturesAdditionallySerializer, BikeTransmissionSerializer
from .serializers.rating import UpdateRatingSerializer
from .serializers.ship import ShipGetSerializer, ShipListSerializer, ShipCreateSerializer, ShipUpdateSerializer, \
    ShipFeaturesAdditionallySerializer, FeaturesEquipmentSerializer
from .serializers.helicopter import HelicopterGetSerializer, HelicopterListSerializer, HelicopterCreateSerializer, \
    HelicopterUpdateSerializer
from .serializers.specialtechnic import SpecialTechnicGetSerializer, SpecialTechnicListSerializer, \
    SpecialTechnicCreateSerializer, SpecialTechnicUpdateSerializer


@extend_schema(summary="Марка транспорта", description="Марка транспорта")
class VehicleBrandViewSet(viewsets.ModelViewSet):
    queryset = VehicleBrand.objects.all()
    serializer_class = VehicleBrandSerializer
    permission_classes = [IsAdminOrReadOnly]


@extend_schema(summary="Модель транспорта", description="Модель транспорта")
class VehicleModelViewSet(viewsets.ModelViewSet):
    queryset = VehicleModel.objects.all().select_related('brand')
    serializer_class = VehicleModelSerializer
    permission_classes = [IsAdminOrReadOnly]


class BaseViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action == 'list':
            self.permission_classes = [AllowAny]
        elif self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated]
        elif self.action == 'create':
            self.permission_classes = [IsAuthenticated, IsAdminOrLessor]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminOrOwner]
        return super().get_permissions()

    def perform_update(self, serializer):
        instance = serializer.save()
        if 'verified' in serializer.validated_data and not self.request.user.role == 'admin':
            instance.verified = False
            instance.save()


@extend_schema(summary="Автомобиль CRUD", description="""Сортировка по цене от меньшего к большему:\n
                                                  URL: ?ordering=rent_prices__price
                                                  \nСортировка по цене от большего к меньшему:\n
                                                  URL: ?ordering=-rent_prices__price""")
class AutoViewSet(BaseViewSet):
    queryset = (Auto.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'features_for_children', 'features_functions', 'photos',
                                 'features_additionally', 'availabilities', 'documents', 'rent_prices'))
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = AutoFilter
    ordering_fields = ['rent_prices__price']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AutoGetSerializer
        elif self.action == 'list':
            return AutoListSerializer
        elif self.action == 'create':
            return AutoCreateSerializer
        return AutoUpdateSerializer


@extend_schema(summary="Мотоцикл", description="Мотоцикл")
class BikeViewSet(BaseViewSet):
    queryset = (Bike.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'features_functions', 'features_additionally', 'availabilities',
                                 'documents', 'rent_prices', 'photos'))
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = BikeFilter
    ordering_fields = ['rent_prices__price']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BikeGetSerializer
        elif self.action == 'list':
            return BikeListSerializer
        elif self.action == 'create':
            return BikeCreateSerializer
        return BikeUpdateSerializer


@extend_schema(summary="Судно", description="Судно")
class ShipViewSet(BaseViewSet):
    queryset = (Ship.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'features_functions', 'features_additionally', 'features_equipment',
                                 'availabilities', 'documents', 'rent_prices', 'photos'))
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = ShipFilter
    ordering_fields = ['rent_prices__price']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ShipGetSerializer
        elif self.action == 'list':
            return ShipListSerializer
        elif self.action == 'create':
            return ShipCreateSerializer
        return ShipUpdateSerializer


@extend_schema(summary="Вертолет", description="Вертолет")
class HelicopterViewSet(BaseViewSet):
    queryset = (Helicopter.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'availabilities', 'documents', 'rent_prices', 'photos'))
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = HelicopterFilter
    ordering_fields = ['rent_prices__price']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HelicopterGetSerializer
        elif self.action == 'list':
            return HelicopterListSerializer
        elif self.action == 'create':
            return HelicopterCreateSerializer
        return HelicopterUpdateSerializer


@extend_schema(summary="Спецтехника", description="Спецтехника")
class SpecialTechnicViewSet(BaseViewSet):
    queryset = (SpecialTechnic.objects.all().select_related('owner', 'brand', 'model').
                prefetch_related('payment_method', 'availabilities', 'documents', 'rent_prices', 'photos'))
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    filterset_class = SpecialTechnicFilter
    ordering_fields = ['rent_prices__price']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SpecialTechnicGetSerializer
        elif self.action == 'list':
            return SpecialTechnicListSerializer
        elif self.action == 'create':
            return SpecialTechnicCreateSerializer
        return SpecialTechnicUpdateSerializer


@extend_schema(summary="Обновление рейтинга", description="Обновить рейтинг может пользователь, который завершил "
                                                          "поездку. Доступно один раз для одного транспорта")
class UpdateRatingView(APIView):
    serializer_class = UpdateRatingSerializer

    def patch(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            vehicle_type = data['Vehicle_type']
            vehicle_id = data['Vehicle_id']

            # Определяем модель транспортного средства
            model = {
                'Auto': Auto,
                'Bike': Bike,
                'Ship': Ship,
                'Helicopter': Helicopter,
                'SpecialTechnic': SpecialTechnic
            }.get(vehicle_type)

            if not model:
                return Response({"error": "Неверный тип транспорта"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                vehicle = model.objects.get(id=vehicle_id)
            except model.DoesNotExist:
                return Response({"error": "Транспорт не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Получаем content_type для данного транспортного средства
            content_type = ContentType.objects.get_for_model(vehicle)

            # Проверка, обновлял ли пользователь уже рейтинг
            if RatingUpdateLog.objects.filter(user=request.user, content_type=content_type,
                                              object_id=vehicle_id).exists():
                return Response({"error": "Вы уже обновили рейтинг этого автомобиля."},
                                status=status.HTTP_403_FORBIDDEN)

            # Пытаемся получить поездку
            try:
                trip = Trip.objects.filter(
                    organizer=request.user,
                    content_type=content_type,
                    object_id=vehicle_id
                ).first()
            except Trip.DoesNotExist:
                return Response({"error": "Не найдено соответствующей поездки"}, status=status.HTTP_404_NOT_FOUND)

            # Проверка завершения поездки
            if trip.status != 'finished':
                return Response({"error": "Поездка еще не завершилась"}, status=status.HTTP_400_BAD_REQUEST)

            # Обновляем рейтинги
            ratings_fields = ['Cleanliness', 'Maintenance', 'Communication', 'Convenience', 'Accuracy']
            for field in ratings_fields:
                rating = data.get(field)
                if rating is not None:
                    field_ratings = vehicle.ratings.get(field, {})
                    star_key = f"{rating}_stars"
                    field_ratings[star_key] = field_ratings.get(star_key, 0) + 1
                    vehicle.ratings[field] = field_ratings

            vehicle.save()

            try:
                lessor = Lessor.objects.get(user=vehicle.owner)
                lessor.count_trip += 1
                lessor.save()
            except Lessor.DoesNotExist:
                return Response({"error": "Арендодатель не найден"}, status=status.HTTP_404_NOT_FOUND)

            # Логируем обновление рейтинга
            RatingUpdateLog.objects.create(
                user=request.user,
                content_type=content_type,
                object_id=vehicle_id
            )

            # Отправка уведомлений
            content = f'Обновлен рейтинг для {vehicle}'
            url = f'{settings.HOST_URL}/vehicle/{content_type}s/{vehicle.id}'
            Notification.objects.create(user=vehicle.owner, content=content, url=url)

            return Response({"status": "Рейтинг успешно обновлен"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="Получение GPS данных", description="Получение GPS данных")
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_gps_location(request):
    vehicle_id = request.data.get('vehicle_id')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    vehicle = Vehicle.objects.get(id=vehicle_id)
    vehicle.latitude = latitude
    vehicle.longitude = longitude
    vehicle.save()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'gps_tracking_{vehicle_id}',
        {
            'type': 'gps_update',
            'latitude': latitude,
            'longitude': longitude
        }
    )

    return Response({"status": "success"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def gps_tracking_view(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    # Проверка прав доступа. следует добавить еще пользователей
    if not request.user != vehicle.owner:
        return Response({"error": "You don't have permission to track this vehicle"}, status=403)

    data = {
        'vehicle_id': vehicle.id,
        'brand': vehicle.brand.name,
        'model': vehicle.model.name,
        'latitude': vehicle.latitude,
        'longitude': vehicle.longitude,
        'last_update': vehicle.last_update.isoformat(),
        'websocket_url': f'/ws/gps_tracking/{vehicle.id}/',
    }

    return Response(data)


@extend_schema(summary="Список функций транспорта", description="Список функций транспорта")
class VehicleFeaturesFunctionsListView(ListAPIView):
    queryset = VehicleFeaturesFunctions.objects.all()
    serializer_class = VehicleFeaturesFunctionsSerializer


@extend_schema(summary="Список дополнительных особенностей авто", description="Список дополнительных особенностей авто")
class AutoFeaturesAdditionallyListView(ListAPIView):
    queryset = AutoFeaturesAdditionally.objects.all()
    serializer_class = AutoFeaturesAdditionallySerializer


@extend_schema(summary="Список дополнительных особенностей мотоциклов", description="Список дополнительных особенностей мотоциклов")
class BikeFeaturesAdditionallyListView(ListAPIView):
    queryset = BikeFeaturesAdditionally.objects.all()
    serializer_class = BikeFeaturesAdditionallySerializer


@extend_schema(summary="Список дополнительных особенностей суден", description="Список дополнительных особенностей суден")
class ShipFeaturesAdditionallyListView(ListAPIView):
    queryset = ShipFeaturesAdditionally.objects.all()
    serializer_class = ShipFeaturesAdditionallySerializer


@extend_schema(summary="Список особенностей авто для детей", description="Список особенностей авто для детей")
class FeaturesForChildrenListView(ListAPIView):
    queryset = FeaturesForChildren.objects.all()
    serializer_class = FeaturesForChildrenSerializer


@extend_schema(summary="Список оборудования для суден", description="Список оборудования для суден")
class FeaturesEquipmentListView(ListAPIView):
    queryset = FeaturesEquipment.objects.all()
    serializer_class = FeaturesEquipmentSerializer


@extend_schema(summary="Список способов платежей", description="Список способов платежей")
class PaymentMethodListView(ListAPIView):
    queryset = PaymentMethod.objects.all()
    serializer_class = PaymentMethodSerializer


@extend_schema(summary="Виды топлива авто", description="Виды топлива")
class AutoFuelTypeListView(ListAPIView):
    queryset = AutoFuelType.objects.all()
    serializer_class = AutoFuelTypeSerializer


@extend_schema(summary="Коробки передач авто", description="Коробки передач для авто")
class AutoTransmissionListView(ListAPIView):
    queryset = AutoTransmission.objects.all()
    serializer_class = AutoTransmissionSerializer


@extend_schema(summary="Типы кузова авто", description="Типы кузова")
class AutoBodyTypeListView(ListAPIView):
    queryset = AutoBodyType.objects.all()
    serializer_class = AutoBodyTypeSerializer


@extend_schema(summary="Коробка передач мотоциклов", description="Коробка передач мотоциклов")
class BikeTransmissionListView(ListAPIView):
    queryset = BikeTransmission.objects.all()
    serializer_class = BikeTransmissionSerializer


@extend_schema(summary="Классы транспорта", description="Классы транспорта")
class VehicleClassListView(ListAPIView):
    queryset = VehicleClass.objects.all()
    serializer_class = VehicleClassSerializer

from datetime import date

from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from app.models import Lessor, User
from chat.models import RequestRent, Chat, Trip
from franchise.models import VehiclePark
from vehicle.models import Vehicle, SpecialTechnic, Helicopter, Ship, Bike, Auto, Availability, VehiclePhoto, \
    VehicleBrand, VehicleModel


class VehiclePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePhoto
        fields = ['photo']


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['start_date', 'end_date']


class LessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lessor
        fields = ['id', 'super_host', 'count_trip']


class UserSerializer(serializers.ModelSerializer):
    lessor = LessorSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['lessor']


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ['name']


class VehicleModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleModel
        fields = ['name']


class VehicleSerializer(serializers.ModelSerializer):
    photos = VehiclePhotoSerializer(many=True, read_only=True)
    availabilities = AvailabilitySerializer(many=True, read_only=True)
    owner = UserSerializer()
    brand = VehicleBrandSerializer(read_only=True)
    model = VehicleModelSerializer(read_only=True)
    type = serializers.SerializerMethodField()
    current_trip = serializers.SerializerMethodField()

    def get_type(self, obj):
        if isinstance(obj, Auto):
            return 'auto'
        elif isinstance(obj, Bike):
            return 'bike'
        elif isinstance(obj, Ship):
            return 'ship'
        elif isinstance(obj, Helicopter):
            return 'helicopter'
        elif isinstance(obj, SpecialTechnic):
            return 'special_technic'
        return 'unknown'

    def get_current_trip(self, obj):
        today = date.today()
        current_trip = Trip.objects.filter(
            content_type=ContentType.objects.get_for_model(obj),
            object_id=obj.id,
            start_date__lte=today,
            end_date__gte=today,
            status__in=['current', 'started']  # Только активные поездки
        ).select_related('organizer').first()

        if current_trip:
            return {
                'organizer_avatar': current_trip.organizer.avatar.url if current_trip.organizer.avatar else None,
                'organizer_first_name': current_trip.organizer.first_name,
                'organizer_last_name': current_trip.organizer.last_name,
                'start_date': current_trip.start_date,
                'end_date': current_trip.end_date
            }
        return None

    class Meta:
        model = Vehicle
        fields = ['id', 'type', 'brand', 'model', 'photos', 'availabilities', 'ratings', 'owner', 'current_trip']


class VehicleParkRetrieveSerializer(serializers.ModelSerializer):
    creator = serializers.StringRelatedField()
    vehicles = VehicleSerializer(many=True, read_only=True)

    class Meta:
        model = VehiclePark
        fields = ['id', 'creator', 'name', 'vehicles']


class VehicleParkListSerializer(serializers.ModelSerializer):
    count_vehicle = serializers.SerializerMethodField()
    creator = serializers.StringRelatedField()

    class Meta:
        model = VehiclePark
        fields = ['id', 'name', 'creator', 'count_vehicle']

    def get_count_vehicle(self, obj):
        return obj.vehicles.count()


class VehicleParkCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePark
        fields = ['name']


class VehicleTypeSerializer(serializers.Serializer):
    vehicle_id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=[
        ('auto', 'Auto'),
        ('bike', 'Bike'),
        ('ship', 'Ship'),
        ('helicopter', 'Helicopter'),
        ('special_technic', 'Special Technic')
    ])


class VehicleParkUpdateSerializer(serializers.ModelSerializer):
    vehicles = VehicleTypeSerializer(many=True, write_only=True)

    class Meta:
        model = VehiclePark
        fields = ['name', 'vehicles']

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        vehicle_data = validated_data.get('vehicles', [])

        for item in vehicle_data:
            vehicle_id = item['vehicle_id']

            vehicle = Vehicle.objects.filter(id=vehicle_id).first()
            if vehicle is None:
                raise serializers.ValidationError(f"Транспортное средство с идентификатором {vehicle_id} не существует.")

            franchise_director = instance.franchise.director if instance.franchise else None

            # Проверка на принадлежность транспортного средства владельцу автопарка или директору франшизы
            if vehicle.owner != instance.owner or vehicle.owner != franchise_director:
                raise serializers.ValidationError(
                    f"Транспортное средство с идентификатором {vehicle_id} не принадлежит владельцу этого парка транспортных средств."
                )

            # Проверяем, что транспорт не принадлежит другому автопарку
            if vehicle.vehicle_park and vehicle.vehicle_park != instance:
                raise serializers.ValidationError(
                    f"Транспортное средство с идентификатором {vehicle_id} уже приписано к другому парку транспортных средств."
                )

            # Устанавливаем автопарк для транспорта
            vehicle.vehicle_park = instance
            vehicle.save()

        instance.save()
        return instance


class OrganizerSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'avatar', 'telephone', 'average_rating']

    def get_average_rating(self, obj):
        renter = getattr(obj, 'renter', None)
        if renter:
            return round(renter.get_average_rating(), 2)
        return 0


class RequestRentSerializer(serializers.ModelSerializer):
    organizer = OrganizerSerializer()
    type = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()
    count_days = serializers.SerializerMethodField()
    chat_id = serializers.SerializerMethodField()

    class Meta:
        model = RequestRent
        fields = [
            'id', 'organizer', 'type', 'status', 'object', 'start_date',
            'end_date', 'count_days', 'total_cost', 'chat_id'
        ]

    def get_type(self, obj):
        return obj.content_type.model

    def get_object(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle) if vehicle else None

    def get_count_days(self, obj):
        if obj.start_date and obj.end_date:
            return (obj.end_date - obj.start_date).days
        return 0

    def get_chat_id(self, obj):
        chat = Chat.objects.filter(request_rent=obj).first()
        return chat.id if chat else None


class ChatSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'request_rent', 'last_message']

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()
        if last_message:
            return {
                "id": last_message.id,
                "content": last_message.content,
                "sender": {
                    "id": last_message.sender.id,
                    "first_name": last_message.sender.first_name,
                    "last_name": last_message.sender.last_name,
                    "avatar": last_message.sender.avatar.url if last_message.sender.avatar else None
                },
                "timestamp": last_message.timestamp.strftime('%H.%m.%y - %H:%M')
            }
        return None


class VehicleParkStatisticsSerializer(serializers.Serializer):
    total_vehicles = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_completed_orders = serializers.IntegerField()
    total_cancelled_orders = serializers.IntegerField()
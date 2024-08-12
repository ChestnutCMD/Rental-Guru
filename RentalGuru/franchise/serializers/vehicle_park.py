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
        fields = ['super_host', 'count_trip']


class UserSerializer(serializers.ModelSerializer):
    lessor = LessorSerializer(read_only=True)  # Nested Lessor data

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

    class Meta:
        model = Vehicle
        fields = ['id', 'type', 'brand', 'model', 'photos', 'availabilities', 'ratings', 'owner']


class VehicleParkRetrieveSerializer(serializers.ModelSerializer):
    vehicles = VehicleSerializer(many=True, read_only=True)

    class Meta:
        model = VehiclePark
        fields = ['id', 'name', 'vehicles']


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
                raise serializers.ValidationError(f"Vehicle with ID {vehicle_id} does not exist.")

            # Проверка на принадлежность транспортного средства владельцу автопарка
            if vehicle.owner != instance.owner:
                raise serializers.ValidationError(
                    f"Vehicle with ID {vehicle_id} does not belong to the owner of this vehicle park."
                )

            # Проверяем, что транспорт не принадлежит другому автопарку
            if vehicle.vehicle_park and vehicle.vehicle_park != instance:
                raise serializers.ValidationError(
                    f"Vehicle with ID {vehicle_id} is already assigned to another vehicle park."
                )

            # Устанавливаем автопарк для транспорта
            vehicle.vehicle_park = instance
            vehicle.save()

        instance.save()
        return instance


class RequestRentSerializer(serializers.ModelSerializer):
    organizer = serializers.StringRelatedField()
    type = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()

    class Meta:
        model = RequestRent
        fields = ['id', 'organizer', 'type', 'status', 'object', 'start_date', 'end_date', 'total_cost']

    def get_type(self, obj):
        return obj.content_type.model

    def get_object(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle) if vehicle else None


class ChatSerializer(serializers.ModelSerializer):
    participants = serializers.StringRelatedField(many=True)

    class Meta:
        model = Chat
        fields = ['id', 'participants']

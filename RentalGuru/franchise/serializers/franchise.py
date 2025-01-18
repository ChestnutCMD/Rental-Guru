from django.db import models
from rest_framework import serializers

from app.models import User, Lessor
from chat.models import RequestRent
from franchise.add_lessor import RequestAddLessor
from franchise.models import Franchise, VehiclePark, Category, RequestFranchise, City
from franchise.serializers.vehicle_park import VehicleParkRetrieveSerializer, VehicleSerializer
from notification.models import Notification
from vehicle.models import Vehicle


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id']


class FranchiseListSerializer(serializers.ModelSerializer):
    director = serializers.StringRelatedField()
    categories = CategorySerializer(many=True)
    avatar = serializers.ImageField(source='director.avatar', read_only=True)

    class Meta:
        model = Franchise
        fields = [
            'id',
            'avatar',
            'director',
            'name',
            'unn',
            'date_register',
            'telephone',
            'email',
            'country',
            'city',
            'commission',
            'total_vehicles',
            'categories'
        ]


class FranchiseRetrieveSerializer(serializers.ModelSerializer):
    vehicle_parks = serializers.SerializerMethodField()
    vehicles = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='director.avatar', read_only=True)

    class Meta:
        model = Franchise
        fields = [
            'avatar',
            'telephone',
            'country',
            'city',
            'vehicle_parks',
            'vehicles',
            'total_vehicles'
        ]

    def get_vehicle_parks(self, obj):
        # Получаем парки у арендодателей, связанных с франшизой, или владельцем которых является директор франшизы
        vehicle_parks = VehiclePark.objects.filter(
            models.Q(owner__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleParkRetrieveSerializer(vehicle_parks, many=True).data

    def get_vehicles(self, obj):
        # Получаем транспорт у арендодателей, связанных с франшизой, или владельцем которого является директор франшизы
        vehicles = Vehicle.objects.filter(
            models.Q(owner__lessor__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleSerializer(vehicles, many=True).data


class FranchiseCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    telephone = serializers.CharField(source='user.telephone')

    class Meta:
        model = Franchise
        fields = ['id', 'name', 'unn', 'telephone', 'country', 'city', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_data = validated_data.pop('user', None)
        if not user_data:
            raise serializers.ValidationError({"user": "Данные пользователя обязательны."})

        email = user_data.get('email')
        if not email:
            raise serializers.ValidationError({"email": "Поле email обязательно для заполнения."})

        first_name = user_data.get('first_name')
        last_name = user_data.get('last_name')
        telephone = user_data.get('telephone')

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже зарегистрирован."})

        password = User.objects.make_random_password()

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            telephone=telephone,
            role='member',
        )

        validated_data["email"] = email
        franchise = Franchise.objects.create(director=user, telephone=user.telephone, **validated_data)

        Notification.objects.create(
            user=user,
            content=f"Добро пожаловать, {first_name}! Вы успешно зарегистрированы как директор франшизы '{franchise.name}'. Ваш пароль: {password}",
        )

        return franchise


class VehicleParkUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePark
        fields = ['id']


class VehicleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id']


class FranchiseUpdateSerializer(serializers.ModelSerializer):
    vehicle_parks = VehicleParkRetrieveSerializer(many=True, read_only=True)
    vehicles = VehicleSerializer(many=True, read_only=True)

    class Meta:
        model = Franchise
        fields = [
            'id',
            'name',
            'director',
            'unn',
            'telephone',
            'country',
            'city',
            'vehicle_parks',
            'vehicles'
        ]

    def get_vehicle_parks(self, obj):
        vehicle_parks = VehiclePark.objects.filter(
            models.Q(lessor__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleParkRetrieveSerializer(vehicle_parks, many=True).data

    def get_vehicles(self, obj):
        vehicles = Vehicle.objects.filter(
            models.Q(owner__lessor__franchise=obj) | models.Q(owner=obj.director)
        )
        return VehicleSerializer(vehicles, many=True).data

    def update(self, instance, validated_data):
        # Обновляем простые поля
        instance.name = validated_data.get('name', instance.name)
        instance.director = validated_data.get('director', instance.director)
        instance.unn = validated_data.get('unn', instance.unn)
        instance.telephone = validated_data.get('telephone', instance.telephone)
        instance.country = validated_data.get('country', instance.country)
        instance.city = validated_data.get('city', instance.city)

        instance.save()
        return instance


class FranchiseDeleteSerializer(serializers.Serializer):
    pass


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

    def get_queryset(self):
        franchise = self.context['franchise']
        return RequestRent.objects.filter(
            models.Q(vehicle__owner__lessor__franchise=franchise) | models.Q(vehicle__owner=franchise.director)
        )


class LessorSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Lessor
        fields = [
            'id',
            'user',
            'super_host',
            'count_trip',
            'average_response_time',
            'franchise'
        ]


class FranchiseStatisticsSerializer(serializers.Serializer):
    total_vehicles = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_margin = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_orders = serializers.IntegerField()
    total_completed_orders = serializers.IntegerField()
    total_cancelled_orders = serializers.IntegerField()
    active_users_count = serializers.IntegerField()


class RequestFranchiseSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestFranchise
        fields = '__all__'


class CitySerializer(serializers.ModelSerializer):
    finished_trips_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = City
        fields = ['id', 'title', 'finished_trips_count']


class RequestAddLessorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestAddLessor
        fields = ['id', 'franchise', 'lessor']
        read_only_fields = ['id']

    def validate(self, attrs):
        request = self.context['request']

        if hasattr(request.user, 'franchise'):
            attrs['franchise'] = request.user.franchise
        elif not attrs.get('franchise'):
            raise serializers.ValidationError(
                "Франшиза обязательна, если пользователь не является директором."
            )

        if RequestAddLessor.objects.filter(
            franchise=attrs['franchise'],
            lessor=attrs['lessor'],
            status='on_consideration'
        ).exists():
            raise serializers.ValidationError(
                "Активная заявка для данного арендодателя уже существует."
            )

        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)
        content = f"Новая заявка № {instance.id} на добавление в франшизу {instance.franchise.name}."
        Notification.objects.create(user=instance.lessor.user, content=content)

        return instance


class RequestAddLessorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestAddLessor
        fields = ['status']

    def validate_status(self, value):
        if value not in ['approved', 'rejected']:
            raise serializers.ValidationError(
                "Статус может быть изменен только на 'approved' или 'rejected'."
            )
        return value

    def validate(self, attrs):
        if self.instance and attrs.get('status') == 'approved':
            if self.instance.lessor.franchise and \
                    self.instance.lessor.franchise != self.instance.franchise:
                raise serializers.ValidationError(
                    "Арендодатель уже привязан к другой франшизе."
                )
        return attrs

    def update(self, instance, validated_data):
        if validated_data['status'] == 'approved':
            instance.lessor.franchise = instance.franchise
            instance.lessor.save()

        instance.status = validated_data['status']
        instance.save()

        if instance.status == 'approved':
            content = f"Ваша заявка на добавление в франшизу {instance.franchise.name} была подтверждена."
        elif instance.status == 'rejected':
            content = f"Ваша заявка на добавление в франшизу {instance.franchise.name} была отклонена."

        Notification.objects.create(user=instance.franchise.director, content=content)
        return instance

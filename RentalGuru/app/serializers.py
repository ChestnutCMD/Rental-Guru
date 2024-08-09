import random
from django.core.cache import cache
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from notification.models import FCMToken
from vehicle.models import Vehicle, Auto, Bike, Ship
from vehicle.serializers.auto import AutoListSerializer
from vehicle.serializers.bike import BikeListSerializer
from vehicle.serializers.helicopter import HelicopterListSerializer
from vehicle.serializers.ship import ShipListSerializer
from vehicle.serializers.specialtechnic import SpecialTechnicListSerializer
from .models import User, Lessor, Renter, RenterDocuments
from .task import send_email_password, send_email_reset_code


class RegisterSerializer(serializers.ModelSerializer):
    member_type = serializers.ChoiceField(choices=[('renter', 'Renter'), ('lessor', 'Lessor')], write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'date_of_birth', 'member_type']

    def create(self, validated_data):
        role = validated_data.pop('member_type')

        # Генерация случайного пароля
        password = get_random_string(length=8)

        user = User.objects.create(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', None),
            last_name=validated_data.get('last_name', None),
            date_of_birth=validated_data.get('date_of_birth', None),
            role='member'
        )
        user.set_password(password)
        user.save()

        # Создание арендатора или арендодателя
        if role == 'lessor':
            Lessor.objects.create(user=user)
        else:
            Renter.objects.create(user=user)

        # Отправка email с паролем
        send_email_password(user.first_name, user.email, password)

        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'role', 'avatar']


class RenterDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RenterDocuments
        fields = ['title', 'number', 'photo']


class RenterDetailSerializer(serializers.ModelSerializer):
    renter_documents = RenterDocumentsSerializer(many=True, read_only=True)

    class Meta:
        model = Renter
        fields = ['favorite', 'verification', 'renter_documents']


class LessorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lessor
        fields = ['super_host', 'count_trip', 'average_response_time']


class UserDetailSerializer(serializers.ModelSerializer):
    renter = RenterDetailSerializer(read_only=True)
    lessor = LessorDetailSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'role', 'avatar',
            'date_of_birth', 'telephone', 'currency', 'about',
            'email_notification', 'push_notification', 'renter', 'lessor'
        ]
        read_only_fields = ['role']

    def update(self, instance, validated_data):
        user_role = self.context['request'].user.role
        if user_role != 'admin':
            if 'role' in validated_data:
                validated_data.pop('role')
            if hasattr(instance, 'renter') and 'renter' in validated_data:
                renter_data = validated_data.pop('renter')
                if 'verification' in renter_data:
                    renter_data.pop('verification')
                for attr, value in renter_data.items():
                    setattr(instance.renter, attr, value)
                instance.renter.save()
            if hasattr(instance, 'lessor') and 'lessor' in validated_data:
                lessor_data = validated_data.pop('lessor')
                if 'super_host' in lessor_data:
                    lessor_data.pop('super_host')
                if 'count_trip' in lessor_data:
                    lessor_data.pop('count_trip')
                if 'average_response_time' in lessor_data:
                    lessor_data.pop('average_response_time')
                for attr, value in lessor_data.items():
                    setattr(instance.lessor, attr, value)
                instance.lessor.save()
        return super().update(instance, validated_data)


class VehicleListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id', 'brand', 'model']

    def to_representation(self, instance):
        if isinstance(instance, Auto):
            return AutoListSerializer(instance).data
        elif isinstance(instance, Bike):
            return BikeListSerializer(instance).data
        elif isinstance(instance, Ship):
            return ShipListSerializer(instance).data
        elif isinstance(instance, Ship):
            return HelicopterListSerializer(instance).data
        elif isinstance(instance, Ship):
            return SpecialTechnicListSerializer(instance).data
        return super().to_representation(instance)


class UpdateRatingSerializer(serializers.Serializer):
    rating = serializers.ChoiceField(choices=[1, 2, 3, 4, 5], required=True)

    def update(self, instance, validated_data):
        rating_value = validated_data['rating']
        rating_field = f"{rating_value}_stars"

        if rating_field in instance.rating:
            instance.rating[rating_field] += 1
        else:
            instance.rating[rating_field] = 1

        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    fcm_token = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        # Проверка last_login
        if not user.last_login:
            data['message'] = "Добро пожаловать! Это ваш первый вход. Рекомендуем сменить пароль."
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # Если FCM-токен передан, то обновляем его
        fcm_token = attrs.get('fcm_token')
        if fcm_token:
            FCMToken.objects.update_or_create(user=user, token=fcm_token, defaults={'last_used_at': timezone.now()})

        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    class Meta:
        fields = ['email']

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с данным email не найден.")
        return value

    def save(self):
        email = self.validated_data['email']
        reset_code = random.randint(1000, 9999)
        cache.set(f"reset_code_{email}", reset_code, timeout=900)
        send_email_reset_code(reset_code, email)


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    reset_code = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    class Meta:
        fields = ['email', 'reset_code', 'new_password']

    def validate(self, data):
        email = data['email']
        reset_code = data['reset_code']

        # Проверка кода в Redis
        stored_code = cache.get(f":1:reset_code_{email}")
        if stored_code != reset_code:
            raise serializers.ValidationError("Неверный код восстановления.")

        return data

    def save(self):
        email = self.validated_data['email']
        new_password = self.validated_data['new_password']

        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()

        # Удаление кода после успешного сброса пароля
        cache.delete(f"reset_code_{email}")
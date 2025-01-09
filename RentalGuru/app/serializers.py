import json
import random
from datetime import datetime
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from franchise.models import Franchise
from influencer.models import Influencer, ReferralLink, QRCode, PromoCode
from notification.models import FCMToken
from vehicle.models import Vehicle, Auto, Bike, Ship
from vehicle.serializers.auto import AutoListSerializer
from vehicle.serializers.bike import BikeListSerializer
from vehicle.serializers.helicopter import HelicopterListSerializer
from vehicle.serializers.ship import ShipListSerializer
from vehicle.serializers.specialtechnic import SpecialTechnicListSerializer
from .models import User, Lessor, Renter, RenterDocuments, FavoriteList, Currency, Language
from RentalGuru.settings import redis_1
from .task import send_verification_email

import logging
logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    date_of_birth = serializers.DateField(required=True)
    member_type = serializers.ChoiceField(choices=[('renter', 'Renter'), ('lessor', 'Lessor')], write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'date_of_birth', 'member_type']

    def create(self, validated_data):
        request = self.context.get('request')
        current_user = request.user if request and request.user.is_authenticated else None
        member_type = validated_data.pop('member_type')
        ref = request.query_params.get('ref', None)
        ref_code = request.query_params.get('code', None)
        promocode = request.query_params.get('promocode', None)

        # Проверка свободного Email
        user = User.objects.filter(email=validated_data['email'])
        if user:
            raise serializers.ValidationError({"Email": "Пользователь с данным Email уже зарегистрирован."})

        code = str(random.randint(1000, 9999))
        date_of_birth_str = validated_data['date_of_birth'].isoformat()
        cache_data = {
            'action': 'registration',
            'email': validated_data['email'],
            'first_name': validated_data.get('first_name'),
            'last_name': validated_data.get('last_name'),
            'date_of_birth': date_of_birth_str,
            'member_type': member_type,
            'status': 'not confirmed',
            'attempts': 0,
            'last_attempt': datetime.now().isoformat(),
            'code': code
        }

        # Обработка инфлюенсера по реферальному коду
        if ref:
            try:
                referral_link = ReferralLink.objects.get(influencer__referral_code=ref, link__icontains=ref_code)
                cache_data['influencer_id'] = referral_link.influencer.id
                cache_data['source_type'] = 'referral'
                cache_data['source_details'] = referral_link.link
            except ReferralLink.DoesNotExist:
                try:
                    qr_code = QRCode.objects.get(influencer__referral_code=ref, referral_link__icontains=ref_code)
                    cache_data['influencer_id'] = qr_code.influencer.id
                    cache_data['source_type'] = 'qr_code'
                    cache_data['source_details'] = qr_code.referral_link
                except QRCode.DoesNotExist:
                    raise serializers.ValidationError({"referral_code": "Неправильный реферальный код или ссылка."})

        elif promocode:
            try:
                promo = PromoCode.objects.get(title=promocode)
                if promo.influencer:
                    cache_data['influencer_id'] = promo.influencer.id
                    cache_data['source_type'] = 'promo'
                    cache_data['source_details'] = promocode
            except PromoCode.DoesNotExist:
                raise serializers.ValidationError({"referral_code": "Неправильный промокод"})

        # Сохранение данных в Redis на 30 минут
        redis_1.set(f"auth_{validated_data['email']}", json.dumps(cache_data), ex=1800)
        send_verification_email.delay(validated_data['email'], code)

        return validated_data


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class EmailVerifiedSerializer(serializers.Serializer):
    verification_code = serializers.CharField(max_length=4)

    def validate_verification_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("Код должен содержать только цифры.")
        return value


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(min_length=4, max_length=4, required=True)


class SetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Старый пароль введен неверно")
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
        fields = ['id', 'title', 'number', 'photo', 'issue_date', 'status']
        read_only_fields = ['id', 'status']

    def validate(self, data):
        if data['title'] == 'license' and not data.get('issue_date'):
            raise serializers.ValidationError({'issue_date': 'Дата выдачи обязательна для документов типа "права".'})
        return data

    def update(self, instance, validated_data):
        request = self.context.get('request')

        if 'status' in validated_data:
            if request and request.user.role not in ('admin', 'manager'):
                raise serializers.ValidationError(
                    {'detail': 'Изменение статуса разрешено только администратору или менеджеру'})

        return super().update(instance, validated_data)


class RenterDetailSerializer(serializers.ModelSerializer):
    renter_documents = RenterDocumentsSerializer(many=True, read_only=True)

    class Meta:
        model = Renter
        fields = ['id', 'user', 'verification', 'renter_documents', 'influencer', 'rating', 'bonus_account']
        read_only_fields = ['id', 'verification', 'influencer', 'rating', 'bonus_account']


class LessorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lessor
        fields = ['super_host', 'count_trip', 'average_response_time', 'commission']


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'code']


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'code']


class InfluencerSerializers(serializers.ModelSerializer):
    class Meta:
        model = Influencer
        fields = ['id']


class UserDetailSerializer(serializers.ModelSerializer):
    renter = RenterDetailSerializer(read_only=True)
    lessor = LessorDetailSerializer(read_only=True)
    influencer = InfluencerSerializers(read_only=True)
    currency = serializers.SlugRelatedField(slug_field='code', queryset=Currency.objects.all())
    language = serializers.SlugRelatedField(slug_field='code', queryset=Language.objects.all())

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'email',
            'email_verified',
            'role',
            'avatar',
            'date_of_birth',
            'telephone',
            'telephone_verified',
            'telegram_id',
            'about',
            'email_notification',
            'push_notification',
            'renter',
            'lessor',
            'influencer',
            'currency',
            'language',
            'date_joined'

        ]
        read_only_fields = ['role', 'date_joined']

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


class VehicleFavoriteList(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = ['id']


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
        try:
            user = User.objects.get(email=attrs['email'])
        except User.DoesNotExist:
            raise ValidationError({'detail': 'Не найдено пользователя с такими учетными данными'})

        if not user.check_password(attrs['password']):
            raise ValidationError({'detail': 'Неверный пароль'})

        data = super().validate(attrs)
        data["user_id"] = user.id

        if hasattr(user, 'manager'):
            if not user.last_login:
                data['message'] = "Добро пожаловать! Это ваш первый вход. Рекомендуем сменить пароль."
            else:
                message = user.manager.check_password_expiry()
                if message:
                    data["message"] = message

        user.last_login = timezone.now()
        try:
            user.save(update_fields=['last_login'])
        except Exception as e:
            raise ValidationError({'detail': f'Ошибка сохранения данных: {e}'})

        # Если FCM-токен передан, то обновляем его
        fcm_token = attrs.get('fcm_token')
        if fcm_token:
            try:
                FCMToken.objects.update_or_create(user=user, token=fcm_token, defaults={'last_used_at': timezone.now()})
            except IntegrityError:
                pass

        return data


class FavoriteListSerializer(serializers.ModelSerializer):
    vehicles = VehicleListSerializer(many=True, read_only=True)

    class Meta:
        model = FavoriteList
        fields = ['id', 'name', 'vehicles', 'created_at', 'updated_at']
        read_only_fields = ['id']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if self.context['request'].parser_context['kwargs'].get('pk'):
            representation['vehicles'] = VehicleListSerializer(
                instance.vehicles.all(), many=True, context=self.context
            ).data
        else:
            representation['vehicles'] = instance.vehicles.count()
        return representation

    def create(self, validated_data):
        vehicles = validated_data.pop('vehicles', [])
        favorite_list = FavoriteList.objects.create(**validated_data)
        favorite_list.vehicles.set(vehicles)
        return favorite_list


class BecomeLessorSerializer(serializers.ModelSerializer):
    franchise = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Lessor.objects.all())

    class Meta:
        model = Lessor
        fields = ['franchise']


class CodeVerificationSerializer(serializers.Serializer):
    verification_code = serializers.CharField(max_length=4)


class TelegramRegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[('lessor', 'Lessor'), ('renter', 'Renter')])
    date_of_birth = serializers.DateField(format='%Y-%m-%d', input_formats=['%Y-%m-%d'])

    class Meta:
        model = User
        fields = ['telegram_id', 'email', 'role', 'date_of_birth', 'first_name', 'last_name']

    def validate(self, data):
        if User.objects.filter(telegram_id=data['telegram_id']).exists():
            raise serializers.ValidationError("Пользователь с таким идентификатором Telegram уже существует")
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Пользователь с таким адресом электронной почты уже существует")
        return data


class OauthProviderSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=['vk', 'mailru', 'yandex'], required=True)
    code = serializers.CharField()
    fcm_token = serializers.CharField(required=False, allow_blank=True)
    ref = serializers.CharField(required=False, allow_blank=True)
    referral_code = serializers.CharField(required=False, allow_blank=True)
    promocode = serializers.CharField(required=False, allow_blank=True)

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password

from vehicle.models import Vehicle, Auto, Bike, Ship
from vehicle.serializers.auto import AutoListSerializer
from vehicle.serializers.base import VehicleBrandSerializer, VehicleModelSerializer
from vehicle.serializers.bike import BikeListSerializer
from vehicle.serializers.helicopter import HelicopterListSerializer
from vehicle.serializers.ship import ShipListSerializer
from vehicle.serializers.specialtechnic import SpecialTechnicListSerializer
from .models import User, Lessor, Renter, RenterDocuments


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    member_type = serializers.ChoiceField(choices=[('renter', 'Renter'), ('lessor', 'Lessor')], write_only=True, required=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password2', 'member_type']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        member_type = validated_data.pop('member_type')

        user = User.objects.create(
            email=validated_data['email'],
            first_name=validated_data.get('first_name', None),
            last_name=validated_data.get('last_name', None),
            role='member'
        )
        user.set_password(validated_data['password'])
        user.save()

        if member_type == 'lessor':
            Lessor.objects.create(user=user)
        else:
            Renter.objects.create(user=user)

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

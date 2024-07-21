from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from vehicle.models import VehicleDocument, Availability, RentPrice, VehiclePhoto, PaymentMethod, VehicleModel, \
    VehicleBrand, VehicleFeaturesFunctions


class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['start_date', 'end_date']
        extra_kwargs = {
            'vehicle': {'required': False}
        }


class VehicleDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleDocument
        fields = ['name', 'image']
        extra_kwargs = {
            'vehicle': {'required': False}
        }


class VehiclePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehiclePhoto
        fields = ['photo']
        extra_kwargs = {
            'vehicle': {'required': False}
        }


class RentPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentPrice
        fields = ['name', 'price', 'commission', 'discount', 'total']
        read_only = 'total'


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = ['name']


class VehicleModelSerializer(serializers.ModelSerializer):
    brand = serializers.PrimaryKeyRelatedField(
        queryset=VehicleBrand.objects.all(),
        required=True
    )

    class Meta:
        model = VehicleModel
        fields = ['name', 'brand']

    def create(self, validated_data):
        brand = validated_data['brand']
        name = validated_data['name']
        vehicle_model = VehicleModel.objects.create(brand=brand, name=name)
        return vehicle_model

    def update(self, instance, validated_data):
        instance.brand = validated_data.get('brand', instance.brand)
        instance.name = validated_data.get('name', instance.name)
        instance.save()
        return instance


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ['name']


class BaseVehicleSerializer(serializers.ModelSerializer):
    payment_method = serializers.PrimaryKeyRelatedField(many=True, queryset=PaymentMethod.objects.all())
    availabilities = AvailabilitySerializer(many=True)
    documents = VehicleDocumentSerializer(many=True)
    photos = VehiclePhotoSerializer(many=True)
    rent_prices = RentPriceSerializer(many=True)
    average_ratings = serializers.SerializerMethodField()

    class Meta:
        fields = '__all__'
        read_only_fields = ['owner', 'ratings', 'average_ratings']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['owner'] = request.user

        availabilities_data = validated_data.pop('availabilities', [])
        documents_data = validated_data.pop('documents', [])
        prices_data = validated_data.pop('rent_prices', [])
        photos_data = validated_data.pop('photos', [])

        vehicle = super().create(validated_data)

        for availability_data in availabilities_data:
            Availability.objects.create(vehicle=vehicle, **availability_data)

        for document_data in documents_data:
            VehicleDocument.objects.create(vehicle=vehicle, **document_data)

        for price_data in prices_data:
            RentPrice.objects.create(vehicle=vehicle, **price_data)

        for photo_data in photos_data:
            VehiclePhoto.objects.create(vehicle=vehicle, **photo_data)

        return vehicle

    @extend_schema_field(serializers.FloatField())
    def get_average_ratings(self, obj):
        return obj.get_average_rating()

    def update(self, instance, validated_data):
        availabilities_data = validated_data.pop('availabilities', [])
        documents_data = validated_data.pop('documents', [])
        prices_data = validated_data.pop('rent_prices', [])
        photos_data = validated_data.pop('photos', [])

        instance = super().update(instance, validated_data)

        instance.availabilities.all().delete()
        for availability_data in availabilities_data:
            Availability.objects.create(vehicle=instance, **availability_data)

        instance.documents.all().delete()
        for document_data in documents_data:
            VehicleDocument.objects.create(vehicle=instance, **document_data)

        instance.rent_prices.all().delete()
        for price_data in prices_data:
            RentPrice.objects.create(vehicle=instance, **price_data)

        instance.rent_prices.all().delete()
        for price_data in prices_data:
            RentPrice.objects.create(vehicle=instance, **price_data)

        instance.rent_prices.all().delete()
        for photo_data in photos_data:
            VehiclePhoto.objects.create(vehicle=instance, **photo_data)
        return instance


class BaseVehicleGetSerializer(serializers.ModelSerializer):
    payment_method = serializers.SerializerMethodField()
    availabilities = AvailabilitySerializer(many=True)
    documents = VehicleDocumentSerializer(many=True)
    photos = serializers.SerializerMethodField()
    rent_prices = RentPriceSerializer(many=True)
    average_ratings = serializers.SerializerMethodField()
    brand = VehicleBrandSerializer(read_only=True)
    model = VehicleModelSerializer(read_only=True)

    class Meta:
        fields = '__all__'
        read_only_fields = ['owner', 'average_ratings']

    @extend_schema_field(serializers.FloatField())
    def get_average_ratings(self, obj):
        return obj.get_average_rating()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_payment_method(self, obj):
        return [payment.name for payment in obj.payment_method.all()]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_photos(self, obj):
        return [i.photo.url for i in obj.photos.all()]


class VehicleFeaturesFunctionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleFeaturesFunctions
        fields = '__all__'


class BaseVehicleListSerializer(serializers.ModelSerializer):
    availabilities = AvailabilitySerializer(many=True)
    photos = serializers.SerializerMethodField()
    rent_prices = RentPriceSerializer(many=True)
    average_ratings = serializers.SerializerMethodField()
    brand = VehicleBrandSerializer(read_only=True)
    model = VehicleModelSerializer(read_only=True)

    class Meta:
        fields = ['brand', 'model', 'average_ratings', 'rent_prices', 'availabilities', 'photos']
        read_only_fields = ['average_ratings']

    @extend_schema_field(serializers.FloatField())
    def get_average_ratings(self, obj):
        return obj.get_average_rating()

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_photos(self, obj):
        return [i.photo.url for i in obj.photos.all()]

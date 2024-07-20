from rest_framework import serializers
from .models import Auto, Bike, Ship, Helicopter, SpecialTechnic, VehicleFeaturesFunctions, ShipFeaturesAdditionally, \
    FeaturesEquipment, BikeFeaturesAdditionally, FeaturesForChildren, AutoFeaturesAdditionally, Availability, \
    VehicleDocument, PaymentMethod, RentPrice, VehicleBrand, VehicleModel


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


class RentPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentPrice
        fields = '__all__'


class VehicleBrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleBrand
        fields = '__all__'


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


class BaseVehicleSerializer(serializers.ModelSerializer):
    payment_method = serializers.PrimaryKeyRelatedField(many=True, queryset=PaymentMethod.objects.all())
    availabilities = AvailabilitySerializer(many=True)
    documents = VehicleDocumentSerializer(many=True)
    rent_prices = RentPriceSerializer(many=True)

    class Meta:
        fields = '__all__'
        read_only_fields = ['owner']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['owner'] = request.user

        availabilities_data = validated_data.pop('availabilities', [])
        documents_data = validated_data.pop('documents', [])
        prices_data = validated_data.pop('rent_prices', [])

        vehicle = super().create(validated_data)

        for availability_data in availabilities_data:
            Availability.objects.create(vehicle=vehicle, **availability_data)

        for document_data in documents_data:
            VehicleDocument.objects.create(vehicle=vehicle, **document_data)

        for price_data in prices_data:
            RentPrice.objects.create(vehicle=vehicle, **price_data)

        return vehicle

    def update(self, instance, validated_data):
        availabilities_data = validated_data.pop('availabilities', [])
        documents_data = validated_data.pop('documents', [])
        prices_data = validated_data.pop('rent_prices', [])

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

        return instance


class AutoSerializer(BaseVehicleSerializer):
    features_for_children = serializers.PrimaryKeyRelatedField(many=True, queryset=FeaturesForChildren.objects.all())
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=AutoFeaturesAdditionally.objects.all())

    class Meta(BaseVehicleSerializer.Meta):
        model = Auto


class BikeSerializer(BaseVehicleSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=BikeFeaturesAdditionally.objects.all())

    class Meta(BaseVehicleSerializer.Meta):
        model = Bike


class ShipSerializer(BaseVehicleSerializer):
    features_functions = serializers.PrimaryKeyRelatedField(many=True, queryset=VehicleFeaturesFunctions.objects.all())
    features_additionally = serializers.PrimaryKeyRelatedField(many=True, queryset=ShipFeaturesAdditionally.objects.all())
    features_equipment = serializers.PrimaryKeyRelatedField(many=True, queryset=FeaturesEquipment.objects.all())

    class Meta(BaseVehicleSerializer.Meta):
        model = Ship


class HelicopterSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = Helicopter


class SpecialTechnicSerializer(BaseVehicleSerializer):
    class Meta(BaseVehicleSerializer.Meta):
        model = SpecialTechnic

from rest_framework import serializers

from chat.models import Trip
from vehicle.models import Vehicle


class TripSerializer(serializers.ModelSerializer):
    organizer = serializers.StringRelatedField()
    type = serializers.SerializerMethodField()
    object = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()  # Добавляем поле owner

    class Meta:
        model = Trip
        fields = ['id', 'organizer', 'type', 'status', 'object', 'start_date', 'end_date', 'total_cost', 'owner']

    def get_type(self, obj):
        return obj.content_type.model

    def get_object(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle) if vehicle else None

    def get_owner(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle.owner) if vehicle and vehicle.owner else None

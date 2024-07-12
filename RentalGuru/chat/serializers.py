from rest_framework import serializers
from .models import Trip, Chat, Message, RequestRent


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['organizer']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organizer'] = request.user
        return super().create(validated_data)


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['sender'] = request.user
        return super().create(validated_data)

class RequestRentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestRent
        fields = '__all__'

    def get_fields(self, *args, **kwargs):
        fields = super().get_fields(*args, **kwargs)
        if self.instance:  # Если это обновление
            for field in fields:
                if field != 'status':
                    fields[field].read_only = True
        return fields

    def create(self, validated_data):
        if validated_data.get('status') != 'unknown':
            validated_data['status'] = 'unknown'
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Проверяем, что только поле status может быть обновлено
        if 'status' in validated_data:
            instance.status = validated_data.get('status', instance.status)
            instance.save(user=self.context['request'].user)
        return instance

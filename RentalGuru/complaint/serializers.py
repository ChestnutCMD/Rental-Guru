from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Complaint
        fields = ['id', 'user', 'vehicle', 'topic', 'description']

    def create(self, validated_data):
        if validated_data.get('topic'):
            validated_data.pop('description', None)
        validated_data.pop('user', None)
        user = self.context['request'].user
        try:
            return Complaint.objects.create(**validated_data)
        except IntegrityError:
            raise ValidationError("Пользователь уже имеет жалобу на этот транспорт.")

    def validate(self, data):
        return super().validate(data)

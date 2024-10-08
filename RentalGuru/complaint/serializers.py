from rest_framework import serializers
from .models import Complaint


class ComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = Complaint
        fields = ['user', 'vehicle', 'topic', 'description']

    def validate(self, data):
        return super().validate(data)

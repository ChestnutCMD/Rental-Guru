from rest_framework import serializers
from .models import Complaint, ComplaintForFeedback, ComplaintForFeedbackRenter


class BaseComplaintSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    def create(self, validated_data):
        request_user = self.context['request'].user
        validated_data['user'] = request_user

        unique_filter = {field: validated_data[field] for field in self.Meta.unique_fields}
        unique_filter['user'] = request_user

        if self.Meta.model.objects.filter(**unique_filter).exists():
            raise serializers.ValidationError("Вы уже подали жалобу на данный объект.")

        return super().create(validated_data)

    def validate(self, data):
        return super().validate(data)


class ComplaintSerializer(BaseComplaintSerializer):
    class Meta:
        model = Complaint
        fields = ['id', 'user', 'vehicle', 'topic', 'description']
        unique_fields = ['vehicle']


class ComplaintFeedbackSerializer(BaseComplaintSerializer):
    class Meta:
        model = ComplaintForFeedback
        fields = ['id', 'user', 'feedback', 'topic', 'description']
        unique_fields = ['feedback']


class ComplaintFeedbackRenterSerializer(BaseComplaintSerializer):
    class Meta:
        model = ComplaintForFeedbackRenter
        fields = ['id', 'user', 'feedback', 'topic', 'description']
        unique_fields = ['feedback']

from app.models import Lessor
from chat.models import Trip

from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum, Max


class LessorReportSerializer(serializers.ModelSerializer):
    last_name = serializers.CharField(source='user.last_name')
    first_name = serializers.CharField(source='user.first_name')
    avatar = serializers.ImageField(source='user.avatar', allow_null=True)
    telephone = serializers.CharField(source='user.telephone', allow_null=True)
    revenue = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    commission_sum = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    last_rental_date = serializers.DateField(read_only=True)

    class Meta:
        model = Lessor
        fields = [
            'id',
            'last_name',
            'first_name',
            'avatar',
            'telephone',
            'revenue',
            'commission_sum',
            'last_rental_date',
        ]
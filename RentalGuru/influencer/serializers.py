from django.db.models import Sum
from rest_framework import serializers

from chat.models import Trip
from influencer.models import Influencer, ReferralLink, InfluencerRequest


class InfluencerSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    referral_code = serializers.CharField(read_only=True)

    class Meta:
        model = Influencer
        fields = ['user_id', 'first_name', 'last_name', 'referral_code']

    def create(self, validated_data):
        user = self.context['request'].user
        influencer = Influencer.objects.create(user=user)
        return influencer


class ReferralLinkSerializer(serializers.ModelSerializer):
    influencer_id = serializers.IntegerField(source='influencer.id', read_only=True)
    influencer_name = serializers.CharField(source='influencer.user.first_name', read_only=True)

    class Meta:
        model = ReferralLink
        fields = ['id', 'influencer_id', 'influencer_name', 'channel', 'link', 'count']
        read_only_fields = ['id', 'influencer_id', 'influencer_name', 'link', 'count']

    def create(self, validated_data):
        validated_data['influencer'] = self.context['request'].user.influencer
        referral_link = ReferralLink.objects.create(**validated_data)
        return referral_link


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLink
        fields = ['channel', 'link', 'count']


class InfluencerDetailSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    referral_links = LinkSerializer(many=True, read_only=True)
    total_clicks = serializers.SerializerMethodField()
    total_rent_income = serializers.SerializerMethodField()

    class Meta:
        model = Influencer
        fields = ['id', 'user_id', 'first_name', 'last_name', 'referral_code', 'referral_links', 'total_clicks', 'total_rent_income']

    def get_total_clicks(self, obj):
        return obj.referral_links.aggregate(total_count=Sum('count'))['total_count'] or 0

    def get_total_rent_income(self, obj):
        renter_users = obj.renters.values_list('user_id', flat=True)
        total_income = Trip.objects.filter(organizer_id__in=renter_users, status='finished').aggregate(total_cost=Sum('total_cost'))
        return total_income['total_cost'] or 0.00


class InfluencerRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerRequest
        fields = ['name', 'city', 'telephone', 'email', 'social', 'description']


class InfluencerRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerRequest
        fields = ['id', 'name', 'city', 'telephone', 'email', 'social', 'description', 'created_at']

from django.db import IntegrityError
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated

from influencer.models import Influencer, ReferralLink
from influencer.permissions import IsAdminOrManager, IsAdminOrInfluencer
from influencer.serializers import InfluencerSerializer, ReferralLinkSerializer, InfluencerDetailSerializer


@extend_schema(summary="Список инфлюенсеров", description="Список инфлюенсеров, доступен только для администраторов.")
class InfluencerListCreateView(ListAPIView, CreateAPIView):
    queryset = Influencer.objects.all()
    serializer_class = InfluencerSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

    def get_queryset(self):
        return Influencer.objects.select_related('user').prefetch_related('referral_links')

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError:
            raise ValidationError({"detail": "Инфлюенсер для данного пользователя уже существует."})


@extend_schema(summary="Детали инфлюенсера", description="Просмотр и удаление инфлюенсера.")
class InfluencerRetrieveDestroyView(RetrieveAPIView, DestroyAPIView):
    queryset = Influencer.objects.all()
    serializer_class = InfluencerDetailSerializer
    permission_classes = [IsAuthenticated, IsAdminOrInfluencer]

    def get_queryset(self):
        return Influencer.objects.select_related('user').prefetch_related('referral_links', 'user__trip_organized_trips')


@extend_schema(summary="Реферальные ссылки", description="Реферальные ссылки")
class ReferralLinkViewSet(viewsets.ModelViewSet):
    queryset = ReferralLink.objects.all()
    serializer_class = ReferralLinkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ReferralLink.objects.select_related('influencer__user')
        return ReferralLink.objects.filter(influencer__user=user).select_related('influencer__user')

    def perform_create(self, serializer):
        serializer.save(influencer=self.request.user.influencer)

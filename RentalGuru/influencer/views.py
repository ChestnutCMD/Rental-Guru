from django.db import IntegrityError
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, CreateAPIView, RetrieveAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from influencer.models import Influencer, ReferralLink, InfluencerRequest
from influencer.permissions import IsAdminOrManager, IsAdminOrInfluencer, IsAdminOrManagerForRequest
from influencer.serializers import InfluencerSerializer, ReferralLinkSerializer, InfluencerDetailSerializer, \
    InfluencerRequestCreateSerializer, InfluencerRequestListSerializer


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


@extend_schema(summary="Заявка на создание инфлюенсера", description="Заявка на создание инфлюенсера")
class InfluencerRequestCreateView(CreateAPIView):
    queryset = InfluencerRequest.objects.all()
    serializer_class = InfluencerRequestCreateSerializer
    permission_classes = [AllowAny]


@extend_schema(summary="Список заявок", description="Возвращает список заявок на создание инфлюенсеров")
class InfluencerRequestListView(ListAPIView):
    queryset = InfluencerRequest.objects.all()
    serializer_class = InfluencerRequestListSerializer
    permission_classes = [IsAdminOrManagerForRequest]


@extend_schema(summary="Удаление заявки", description="Удаление заявки")
class InfluencerRequestDeleteView(DestroyAPIView):
    queryset = InfluencerRequest.objects.all()
    serializer_class = InfluencerRequestListSerializer
    permission_classes = [IsAdminOrManagerForRequest]

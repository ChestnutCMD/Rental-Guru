from django.db import transaction
from django.utils.timezone import now
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, CreateAPIView, DestroyAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from influencer.models import Influencer, ReferralLink, InfluencerRequest, QRCode, PromoCode, UsedPromoCode
from influencer.permissions import IsAdminOrManager, IsAdminOrInfluencer, IsAdminOrManagerForRequest
from influencer.serializers import InfluencerSerializer, ReferralLinkSerializer, InfluencerDetailSerializer, \
    InfluencerRequestCreateSerializer, InfluencerRequestListSerializer, QRCodeSerializer, PromoCodeSerializer, \
    InfluencerListSerializer


class InfluencerViewSet(ModelViewSet):
    """
    Вьюсет для управления инфлюенсерами: создание, просмотр списка, детали, удаление.
    """
    queryset = Influencer.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['retrieve', 'destroy', 'update', 'partial_update']:
            return InfluencerDetailSerializer
        if self.action == 'list':
            return InfluencerListSerializer
        return InfluencerSerializer

    def get_permissions(self):
        if self.action in ['list', 'create']:
            return [permission() for permission in [IsAdminOrManager]]
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return [permission() for permission in [IsAdminOrInfluencer]]
        return super().get_permissions()

    def get_queryset(self):
        return Influencer.objects.select_related('user').prefetch_related('referral_links',
                                                                          'user__trip_organized_trips')

    @extend_schema(
        summary="Список инфлюенсеров",
        description="Список инфлюенсеров, доступен только для администраторов и менеджеров."
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Создание инфлюенсера",
        description="Создание инфлюенсера с автоматической генерацией пароля."
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        influencer = serializer.save()
        return Response(
            InfluencerSerializer(influencer).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        summary="Детали инфлюенсера",
        description="Просмотр и удаление инфлюенсера."
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Удаление инфлюенсера и связанного пользователя."""
        instance = self.get_object()

        with transaction.atomic():
            user = instance.user
            user.delete()

            instance.delete()

        return Response(
            {"message": "Инфлюенсер и связанный пользователь успешно удалены."},
            status=status.HTTP_204_NO_CONTENT,
        )


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


class QRCodeViewSet(viewsets.ModelViewSet):
    queryset = QRCode.objects.all()
    serializer_class = QRCodeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Возвращает QR-коды только текущего пользователя."""
        user = self.request.user
        if user.role == 'admin':
            return QRCode.objects.select_related('influencer__user')
        return QRCode.objects.filter(influencer__user=self.request.user).select_related('influencer', 'influencer__user')

    def perform_create(self, serializer):
        """Добавляет текущего пользователя как инфлюенсера."""
        try:
            influencer = self.request.user.influencer
            serializer.save(influencer=influencer)
        except Influencer.DoesNotExist:
            raise ValidationError({"detail": "У текущего пользователя нет связанного инфлюенсера."})

    @action(detail=True, methods=['get'], url_path='download-qr-code')
    def download_qr_code(self, request, pk=None):
        """Возвращает файл QR-кода для скачивания."""
        qr_code = self.get_object()
        if not qr_code.qr_code_image:
            return Response({"detail": "QR-код еще не сгенерирован."}, status=400)

        response = Response()
        response['Content-Disposition'] = f'attachment; filename="{qr_code.qr_code_image.name}"'
        response['X-Accel-Redirect'] = qr_code.qr_code_image.url
        return response


@extend_schema(summary="Промокоды", description="CRUD промокодов")
class PromoCodeViewSet(ModelViewSet):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAdminOrManagerForRequest]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager']:
            return PromoCode.objects.all()
        elif hasattr(user, 'influencer') and user.influencer:
            return PromoCode.objects.filter(influencer=user.influencer)
        return PromoCode.objects.none()

    def get_permissions(self):
        """
        Используем разные permissions для разных методов.
        """
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminOrManager()]


class ApplyPromoCodeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Применить промокод",
        description="Применение промокода",
        request={
            'application/json': {
                'promocode': 'string',
            }
        },
        responses={
            200: {'message': 'Промокод успешно применен.'},
            400: {'message': 'Ошибка при применении промокода.'}
        }
    )
    def post(self, request):
        if not hasattr(request.user, 'renter'):
            raise ValidationError('Доступно только для пользователей с ролью арендатора.')

        user = request.user
        promo_code_title = request.data.get('promocode')

        if not promo_code_title:
            raise ValidationError('Не указан промокод.')

        try:
            promo_code = PromoCode.objects.get(title=promo_code_title)
        except PromoCode.DoesNotExist:
            raise ValidationError('Промокод не найден.')

        if promo_code.expiration_date and promo_code.expiration_date < now():
            raise ValidationError('Срок действия промокода истек.')

        if UsedPromoCode.objects.filter(user=user, promo_code=promo_code, used=False).exists():
            raise ValidationError('Вы уже применили этот промокод.')

        if UsedPromoCode.objects.filter(user=user, promo_code=promo_code, used=True).exists():
            raise ValidationError('Вы уже использовали этот промокод.')
        try:
            with transaction.atomic():
                if promo_code.type == 'cash':
                    user.renter.bonus_account += promo_code.total
                    user.renter.save()
                    UsedPromoCode.objects.create(user=user, promo_code=promo_code, used=True)
                    promo_code.count += 1
                    promo_code.save()
                    return Response({'message': 'Промокод успешно применен.'})
        except Exception as e:
            raise ValidationError({'message': f'Ошибка при применении промокода: {str(e)}'})

        UsedPromoCode.objects.create(user=user, promo_code=promo_code)
        promo_code.count += 1
        promo_code.save()

        return Response({'message': 'Промокод успешно применен.'})

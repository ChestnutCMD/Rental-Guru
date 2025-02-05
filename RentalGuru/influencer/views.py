from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, CreateAPIView, DestroyAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from influencer.models import Influencer, ReferralLink, InfluencerRequest, QRCode, PromoCode, UsedPromoCode, \
    RequestWithdraw, RegistrationSource
from influencer.permissions import IsAdminOrManager, IsAdminOrInfluencer, IsAdminOrManagerForRequest
from influencer.serializers import InfluencerSerializer, ReferralLinkSerializer, InfluencerDetailSerializer, \
    InfluencerRequestCreateSerializer, InfluencerRequestListSerializer, QRCodeSerializer, PromoCodeSerializer, \
    InfluencerListSerializer, RequestWithdrawSerializer, PaymentSerializer
from manager.permissions import ManagerObjectPermission
from payment.models import Payment
from .tasks import withdraw_request


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
        user = self.request.user

        if user.role in ['admin', 'manager']:
            return Influencer.objects.select_related(
                'user',
                'organization',
                'organization__bank_details'
            ).prefetch_related(
                'referral_links',
                'user__trip_organized_trips'
            )

        if hasattr(user, 'influencer') and user.influencer:
            return Influencer.objects.filter(id=user.influencer.id).select_related(
                'user',
                'organization',
                'organization__bank_details'
            ).prefetch_related(
                'referral_links',
                'user__trip_organized_trips'
            )

        return Influencer.objects.none()

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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['influencer__id']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            queryset = ReferralLink.objects.select_related('influencer__user')
            influencer_id = self.request.query_params.get('influencer_id')
            if influencer_id:
                queryset = queryset.filter(influencer__id=influencer_id)
            return queryset
        return ReferralLink.objects.filter(influencer__user=user).select_related('influencer__user')

    def perform_create(self, serializer):
        serializer.save(influencer=self.request.user.influencer)


@extend_schema(summary="CRUD QR кодов", description="CRUD QR кодов")
class QRCodeViewSet(viewsets.ModelViewSet):
    queryset = QRCode.objects.all()
    serializer_class = QRCodeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['influencer__id']

    def get_queryset(self):
        """Возвращает QR-коды только текущего пользователя."""
        user = self.request.user
        if user.role == 'admin':
            queryset = QRCode.objects.select_related('influencer', 'influencer__user')
            influencer_id = self.request.query_params.get('influencer_id')
            if influencer_id:
                queryset = queryset.filter(influencer__id=influencer_id)
            return queryset
        return QRCode.objects.filter(influencer__user=user).select_related('influencer', 'influencer__user')

    def perform_create(self, serializer):
        """Добавляет текущего пользователя как инфлюенсера."""
        try:
            influencer = self.request.user.influencer
            serializer.save(influencer=influencer)
        except Influencer.DoesNotExist:
            raise ValidationError({"detail": "У текущего пользователя нет связанного инфлюенсера."})

    @extend_schema(summary="Скачать QR код", description="Скачать QR код")
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
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['influencer__id']

    def get_queryset(self):
        user = self.request.user
        queryset = PromoCode.objects.all()

        if user.role in ['admin', 'manager']:
            influencer_id = self.request.query_params.get('influencer_id')
            if influencer_id:
                queryset = queryset.filter(influencer__id=influencer_id)
            return queryset

        if hasattr(user, 'influencer') and user.influencer:
            return queryset.filter(influencer=user.influencer)

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
                'type': 'object',
                'properties': {
                    'promocode': {
                        'type': 'string',
                        'description': 'Промокод, который нужно применить'
                    }
                },
                'required': ['promocode'],
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


class RequestWithdrawViewSet(viewsets.ModelViewSet):
    serializer_class = RequestWithdrawSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        Переопределяем метод get_permissions для разных операций.
        """
        if self.action in ['create', 'list', 'retrieve']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), ManagerObjectPermission()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'influencer'):
            return RequestWithdraw.objects.filter(influencer=user.influencer)
        elif user.role in ['admin', 'manager']:
            return RequestWithdraw.objects.all()
        return RequestWithdraw.objects.none()

    def perform_update(self, serializer):
        if serializer.validated_data.get('status') == 'completed' and not serializer.validated_data.get('payment_date'):
            serializer.validated_data['payment_date'] = timezone.now()
        serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status == 'completed' and instance.payment_date is None:
            return Response({"detail": "Дата выплаты должна быть установлена при статусе 'Выполнено'."}, status=400)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


@extend_schema(summary="Вывод транзакций", description="Вывод транзакций")
class InfluencerPaymentsView(ListAPIView):
    """
    Вью для вывода платежей по конкретному инфлюенсеру.
    """
    permission_classes = [IsAdminOrManager]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        influencer_id = self.kwargs.get('influencer_id')
        get_object_or_404(Influencer, id=influencer_id)
        return Payment.objects.filter(influencer_id=influencer_id).select_related('request_rent', 'influencer').order_by('-updated_at')  # TODO добавить фильтр для оплаченый платежей


PERIODS = {
    'day': timedelta(days=1),
    'week': timedelta(weeks=1),
    'month': timedelta(days=30),
    'quarter': timedelta(days=90),
    'year': timedelta(days=365),
    'all': None
}


@extend_schema(
    summary="Вывод статистики",
    description="Вывод статистики",
    parameters=[
        OpenApiParameter(
                name="period",
                description="Период для фильтрации (day, week, month, quarter, year)",
                type=str,
                enum=["day", "week", "month", "quarter", "year"],
                required=False,)
                ]
)
class InfluencerStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'influencer'):
            return Response({"detail": "Вы не являетесь инфлюенсером."}, status=403)

        influencer = user.influencer
        period = request.query_params.get('period', 'all')
        if period not in PERIODS:
            return Response({"detail": "Неверно указан период."}, status=400)

        current_period = PERIODS[period]
        prev_period = PERIODS[period] if period != 'all' else None

        def get_period_filter(period_delta):
            if period_delta:
                return now() - period_delta
            return None

        current_start = get_period_filter(current_period)
        prev_start = get_period_filter(prev_period)

        current_filter = {"created_at__gte": current_start} if current_start else {}
        prev_filter = {"created_at__gte": prev_start, "created_at__lt": current_start} if prev_start else {}

        count_clients = Payment.objects.filter(influencer=influencer, **current_filter).count()
        total = Payment.objects.filter(influencer=influencer, **current_filter).aggregate(total=Sum('amount'))['total'] or 0
        revenue = total * influencer.commission / 100
        count_register = RegistrationSource.objects.filter(influencer=influencer, **current_filter).count()

        prev_count_clients = Payment.objects.filter(influencer=influencer, **prev_filter).count()
        prev_total = Payment.objects.filter(influencer=influencer, **prev_filter).aggregate(total=Sum('amount'))['total'] or 0
        prev_revenue = prev_total * influencer.commission / 100
        prev_count_register = RegistrationSource.objects.filter(influencer=influencer, **prev_filter).count()

        def calculate_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return round(((current - previous) / previous) * 100, 2)

        return Response({
            "count_clients": count_clients,
            "revenue": revenue,
            "count_register": count_register,
            "change_count_clients": calculate_change(count_clients, prev_count_clients),
            "change_revenue": calculate_change(revenue, prev_revenue),
            "change_count_register": calculate_change(count_register, prev_count_register)
        })


@extend_schema(summary="Вывод статистики", description="Вывод статистики")
class InfluencerWithdrawRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, 'influencer'):
            return Response({"detail": "Вы не являетесь инфлюенсером."}, status=403)

        amount = request.data.get("amount")
        if not amount or float(amount) <= 0:
            return Response({"detail": "Некорректная сумма."}, status=400)

        influencer = user.influencer
        withdraw_request.delay(amount, influencer.user.get_full_name())
        return Response({"detail": "Запрос на вывод средств отправлен."}, status=200)

import hashlib
import hmac
import json
import random
from datetime import datetime, timedelta, date
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.timezone import now
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404, ListAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.test import APIRequestFactory
from social_django.utils import load_strategy, load_backend
from social_core.exceptions import AuthForbidden, AuthTokenError

from RentalGuru import settings
from RentalGuru.settings import redis_1
from chat.models import Trip
from franchise.models import Franchise
from influencer.models import Influencer
from notification.models import Notification
from vehicle.models import Vehicle
from .filters import RenterDocumentsFilter
from .models import User, RenterDocuments, Renter, Rating, FavoriteList, Lessor, Currency, Language
from .permissions import IsAdminOrSelf, IsAdmin
from .serializers import RegisterSerializer, ChangePasswordSerializer, UserListSerializer, UserDetailSerializer, \
    RenterDocumentsSerializer, VehicleListSerializer, UpdateRatingSerializer, CustomTokenObtainPairSerializer, \
    PasswordResetRequestSerializer, FavoriteListSerializer, VerifyCodeSerializer, SetPasswordSerializer, \
    BecomeLessorSerializer, CurrencySerializer, LanguageSerializer, CodeVerificationSerializer
from .task import send_verification_email, send_sms


@extend_schema(summary="Смена пароля", description="Смена пароля")
class ChangePasswordView(APIView):
    """Смена пароля"""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def put(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Восстановление пароля",
    description="Восстановление пароля по email",
    request=PasswordResetRequestSerializer,
    responses={200: None}
)
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        try:
            User.objects.get(email=request.data.get('email'))
        except User.DoesNotExist:
            return Response({"message": "Пользователя с таким Email не существует"}, status=status.HTTP_404_NOT_FOUND)

        verification_code = str(random.randint(1000, 9999))

        cache_data = {
            'action': 'reset_password',
            'email': email,
            'code': verification_code,
            'attempts': 0,
            'last_attempt': datetime.now().isoformat()
        }

        redis_1.set(f"auth_{email}", json.dumps(cache_data), ex=1800)  # 30 минут
        send_verification_email.delay(email, verification_code)

        return Response({"message": "Код для сброса пароля отправлен на вашу почту."}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Проверка кода для пароля",
    description="Проверка кода для пароля",
    request=VerifyCodeSerializer,
    responses={200: None}
)
class VerifyCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        code = serializer.validated_data['code']

        cached_data = redis_1.get(f"auth_{email}")
        if cached_data is None:
            return Response({"error": "Недействительный или просроченный код."}, status=status.HTTP_400_BAD_REQUEST)

        cache_data = json.loads(cached_data.decode('utf-8'))

        last_attempt = datetime.fromisoformat(cache_data['last_attempt'])
        if cache_data['attempts'] >= 3 and (datetime.now() - last_attempt) < timedelta(minutes=10):
            time_left = timedelta(minutes=10) - (datetime.now() - last_attempt)
            return Response(
                {"error": f"Слишком много попыток. Пожалуйста, попробуйте через {time_left.seconds // 60} минут."},
                status=status.HTTP_400_BAD_REQUEST)

        if cache_data['code'] != code:
            cache_data['attempts'] += 1
            cache_data['last_attempt'] = datetime.now().isoformat()
            redis_1.set(f"auth_{email}", json.dumps(cache_data), ex=1800)
            return Response({"error": "Неверный код."}, status=status.HTTP_400_BAD_REQUEST)

        cache_data['status'] = 'confirmed'
        cache_data['attempts'] = 0
        redis_1.set(f"auth_{email}", json.dumps(cache_data), ex=1800)
        return Response({"message": "Код успешно подтвержден."}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Создание пароля",
    description="Создание пароля",
    request=SetPasswordSerializer,
    responses={200: None}
)
class SetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']

        cached_data = redis_1.get(f"auth_{email}")
        if cached_data is None:
            return Response({"error": "Недействительный или просроченный запрос."}, status=status.HTTP_400_BAD_REQUEST)

        cache_data = json.loads(cached_data.decode('utf-8'))

        if cache_data.get('status') != 'confirmed':
            return Response({"error": "Код не подтвержден."}, status=status.HTTP_400_BAD_REQUEST)

        if cache_data['action'] == 'registration':

            # Создание пользователя
            date_of_birth = date.fromisoformat(cache_data['date_of_birth'])
            user = User.objects.create_user(
                email=cache_data['email'],
                password=password,
                first_name=cache_data['first_name'],
                last_name=cache_data['last_name'],
                date_of_birth=date_of_birth,
                role='member'
            )

            # Привязка к франшизе или инфлюенсеру
            if cache_data['member_type'] == 'lessor' and cache_data.get('franchise_id'):
                franchise = Franchise.objects.get(id=cache_data['franchise_id'])
                Lessor.objects.create(user=user, franchise=franchise)
            elif cache_data['member_type'] == 'renter' and cache_data.get('influencer_id'):
                influencer = Influencer.objects.get(id=cache_data['influencer_id'])
                Renter.objects.create(user=user, influencer=influencer)
            elif cache_data['member_type'] == 'lessor':
                Lessor.objects.create(user=user)
            elif cache_data['member_type'] == 'renter':
                Renter.objects.create(user=user)
            message = "Пользователь успешно зарегистрирован."
        elif cache_data['action'] == 'reset_password':
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            message = "Пароль успешно изменен."
        else:
            return Response({"error": "Неверный тип действия."}, status=status.HTTP_400_BAD_REQUEST)

        redis_1.delete(f"auth_{email}")
        return Response({"message": message}, status=status.HTTP_200_OK)


@extend_schema(summary="Пользователи CRUD", description="""\nРегистрация, получение списка пользователей, 
                                                            получение пользователя по ID, обновление, удаление.
                                                            Метод пост может принимать параметры:\n
                            /?ref=<referral_code>&code=<link_code>""")
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return RegisterSerializer
        elif self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        elif self.action in ['update', 'partial_update', 'destroy', 'retrieve']:
            permission_classes = [IsAuthenticated, IsAdminOrSelf]
        elif self.action == 'list':
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            permission_classes = [IsAuthenticated, IsAdminOrSelf]
        return [permission() for permission in permission_classes]

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response({"message": "Код подтверждения отправлен на вашу почту."}, status=status.HTTP_200_OK)


@extend_schema(summary="Документы арендаторы", description="Документы арендатора")
class RenterDocumentsViewSet(viewsets.ModelViewSet):
    serializer_class = RenterDocumentsSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = RenterDocumentsFilter
    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin' or user.role == 'manager':
            return RenterDocuments.objects.all()
        else:
            try:
                renter = user.renter
            except ObjectDoesNotExist:
                return RenterDocuments.objects.none()
            return RenterDocuments.objects.filter(renter=renter)

    def perform_create(self, serializer):
        user = self.request.user
        try:
            renter = user.renter
        except ObjectDoesNotExist:
            raise Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(renter=renter)

    def perform_update(self, serializer):
        user = self.request.user
        document = self.get_object()

        if user.role == 'admin' or user.role == 'manager':
            if serializer.valvalidated_data.get('status') == 'approved':
                url = f'{settings.HOST_URL}' #TODO добавить ссылку
                content = f'Ваш документ проверен'
                Notification.objects.create(user=document.renter.user, url=url, content=content)
            elif serializer.valvalidated_data.get('status') == 'rejected':
                url = f'{settings.HOST_URL}' #TODO добавить ссылку
                content = f'Ваш документ отклонен'
                Notification.objects.create(user=document.renter.user, url=url, content=content)
            serializer.save()
        else:
            # Запрещаем изменять статус для обычных пользователей
            if 'status' in serializer.validated_data:
                return Response({'detail': 'Изменение статуса запрещено'}, status=status.HTTP_403_FORBIDDEN)

            serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        try:
            renter = user.renter
        except ObjectDoesNotExist:
            raise Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)
        if instance.renter != renter:
            raise Response({'detail': 'Документ не принадлежит текущему арендатору'},
                           status=status.HTTP_400_BAD_REQUEST)
        instance.delete()


@extend_schema(summary="Списки избранного", description="Списки избранного")
class FavoriteListViewSet(viewsets.ModelViewSet):
    serializer_class = FavoriteListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavoriteList.objects.filter(renter=self.request.user.renter)

    def perform_create(self, serializer):
        serializer.save(renter=self.request.user.renter)

    @action(detail=True, methods=['post'])
    def add_vehicle(self, request, pk=None):
        favorite_list = self.get_object()
        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'detail': 'Требуется ID транспортного средства'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            favorite_list.vehicles.add(vehicle)
            # Удаляем из общего избранного, если он там был
            request.user.renter.favorite.remove(vehicle)
            return Response({'detail': 'Транспорт добавлен в список и удален из общего избранного'}, status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_vehicle(self, request, pk=None):
        favorite_list = self.get_object()
        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'detail': 'Требуется ID транспортного средства'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            favorite_list.vehicles.remove(vehicle)
            return Response({'detail': 'Транспорт удален из списка'}, status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="Создать новый список избранного",
        description="Создает новый пустой список избранного или список с указанными транспортными средствами",
        request=FavoriteListSerializer,
        responses={201: FavoriteListSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @extend_schema(
        summary="Получить детальную информацию о списке избранного",
        description="Возвращает детальную информацию о списке избранного, включая полные данные о транспортных средствах",
        responses={200: FavoriteListSerializer},
    )
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@extend_schema(summary="Избранный транпорт", description="Избранный транпорт арендатора. Эндпоинты app/favorite/add/ "
                                                         "и app/favorite/remove/ принимают {'vehicle_id': id} для "
                                                         "добавления и удаления в список избранного соответственно")
class FavoriteVehicleViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        favorites = renter.favorite.all()
        serializer = VehicleListSerializer(favorites, many=True)
        return Response({'favorites': serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch'], url_path='add', url_name='add_favorite')
    def add_favorite(self, request):
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'detail': 'Требуется ID транспортного средства'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            renter.favorite.add(vehicle)
            return Response({'detail': 'Транспорт добавлен в общее избранное'}, status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['patch'], url_path='remove', url_name='remove_favorite')
    def remove_favorite(self, request):
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle_id = request.data.get('vehicle_id')
        if not vehicle_id:
            return Response({'detail': 'Требуется ID транспортного средства'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            renter.favorite.remove(vehicle)
            return Response({'detail': 'Транспорт удален из общего избранного'}, status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], url_path='move_to_list', url_name='move_to_list')
    def move_to_list(self, request):
        user = request.user
        try:
            renter = user.renter
        except Renter.DoesNotExist:
            return Response({'detail': 'Пользователь не является арендатором'}, status=status.HTTP_400_BAD_REQUEST)

        vehicle_id = request.data.get('vehicle_id')
        list_id = request.data.get('list_id')

        if not vehicle_id or not list_id:
            return Response({'detail': 'Требуется ID транспортного средства и ID списка'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            vehicle = Vehicle.objects.get(id=vehicle_id)
            favorite_list = FavoriteList.objects.get(id=list_id, renter=renter)

            # Удаляем из общего избранного и добавляем в конкретный список
            renter.favorite.remove(vehicle)
            favorite_list.vehicles.add(vehicle)

            return Response({'detail': 'Транспорт перемещен из общего избранного в указанный список'}, status=status.HTTP_200_OK)
        except Vehicle.DoesNotExist:
            return Response({'detail': 'Транспорт не найден'}, status=status.HTTP_404_NOT_FOUND)
        except FavoriteList.DoesNotExist:
            return Response({'detail': 'Список избранного не найден'}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(summary="Обновление рейтинга арендатора", description="Выставляется владельцем транспорта, после "
                                                                     "завершения поездки. Принимает JSON: {"
                                                                     "'rating': 5}")
class UpdateRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, renter_id):
        renter = get_object_or_404(Renter.objects.select_related('user'), id=renter_id)
        user = request.user

        # Получаем все поездки арендатора и проверяем, что текущий пользователь является владельцем транспортного средства в одной из завершённых поездок
        trips = Trip.objects.filter(organizer=renter.user, end_date__lt=now()).select_related(
            'content_type').prefetch_related('vehicle')

        is_owner = any(trip.vehicle.owner == user for trip in trips)

        if not is_owner:
            return Response({
                                "detail": "Вы не являетесь владельцем транспортного средства в завершённых поездках данного арендатора."},
                            status=status.HTTP_403_FORBIDDEN)

        # Проверяем, что текущий пользователь еще не оставлял рейтинг этому арендатору
        if Rating.objects.filter(user=user, renter=renter).exists():
            return Response({"detail": "Вы уже оставляли рейтинг этому арендатору."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = UpdateRatingSerializer(data=request.data)

        if serializer.is_valid():
            # Обновляем рейтинг арендатора
            serializer.update(renter, serializer.validated_data)

            # Сохраняем информацию о рейтинге
            Rating.objects.create(user=user, renter=renter, rating=serializer.validated_data['rating'])

            return Response({"average_rating": renter.get_average_rating()}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="Получение JWT токенов", description="Принимает email и password (опционально fcm_token для "
                                                            "пуш уведомлений). При первом входе предлагает сменить "
                                                            "пароль")
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(summary="Вход через социальные сети", description="Вход и регистрация. Принимает токен и название "
                                                                 "провайдера: Яндекс — yandex-oauth2\nMail.ru — "
                                                                 "mailru-oauth2\nGoogle — google-oauth2\nVK ("
                                                                 "ВКонтакте) — vk-oauth2")
class SocialAuthView(APIView):
    def post(self, request, *args, **kwargs):
        provider = request.data.get('provider')
        token = request.data.get('token')

        if not all([provider, token]):
            return Response(
                {"error": "Provider and token are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            strategy = load_strategy(request)
            backend = load_backend(strategy=strategy, name=provider, redirect_uri=None)

            try:
                user_social_auth = backend.do_auth(token)
            except (AuthForbidden, AuthTokenError) as e:
                return Response(
                    {"error": f"Invalid token: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if user_social_auth is None:
                return Response(
                    {"error": "Authentication failed"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if user_social_auth.is_new:
                Renter.objects.create(user=user_social_auth.user)

            refresh = RefreshToken.for_user(user_social_auth.user)

            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user_social_auth.user.id,
                    "email": user_social_auth.user.email,
                    "first_name": user_social_auth.user.first_name,
                    "last_name": user_social_auth.user.last_name,
                    "is_new": user_social_auth.is_new,
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Authentication failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(summary="Стать арендодателем", description="Удаление арендатора и создание арендодателя")
class BecomeLessorView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            renter = Renter.objects.get(user=user)
        except Renter.DoesNotExist:
            return Response({"detail": "User is not a Renter"}, status=status.HTTP_400_BAD_REQUEST)

        renter.delete()

        serializer = BecomeLessorSerializer(data=request.data)
        if serializer.is_valid():
            Lessor.objects.create(user=user, **serializer.validated_data)
            return Response({"detail": "Пользователь был успешно переведен в арендодателя"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="Список валют", description="Список валют")
class CurrencyListView(ListAPIView):
    queryset = Currency.objects.all()
    serializer_class = CurrencySerializer


@extend_schema(summary="Список языков", description="Список языков")
class LanguageListView(ListAPIView):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


@extend_schema(summary="Отправка кода на номер телефона", description="Отправка кода на номер телефона")
class PhoneSendCode(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.telephone:
            return Response({"detail": "Номер телефона пользователя не найден."}, status=status.HTTP_400_BAD_REQUEST)
        elif user.telephone_verified:
            return Response({"detail": "Номер телефона уже верифицирован"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            verification_code = random.randint(1000, 9999)
            redis_1.set(f'phone_{user.telephone}', json.dumps(verification_code), ex=1800)
            send_sms.delay(user.telephone, verification_code)
            return Response({"detail": "Код подтверждения отправлен."}, status=status.HTTP_200_OK)


@extend_schema(summary="Верификация номера телефона", description="Верификация номера телефона")
class PhoneVerifyCode(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CodeVerificationSerializer

    def post(self, request):
        user = request.user
        serializer = CodeVerificationSerializer(data=request.data)

        if serializer.is_valid():
            verification_code = serializer.validated_data['verification_code']
            stored_code = redis_1.get(f'phone_{user.telephone}')

            if stored_code is None:
                return Response({"detail": "Срок действия кода подтверждения истек или он недействителен."}, status=status.HTTP_400_BAD_REQUEST)

            if str(json.loads(stored_code)) == str(verification_code):
                user.telephone_verified = True
                user.save()
                redis_1.delete(f'phone_{user.telephone}')
                return Response({"detail": "Номер телефона подтвержден"}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Неверный код подтверждения."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    summary="Callback для телеграма",
    description="Callback для телеграма"
)
class TelegramCallbackView(APIView):
    def post(self, request):
        data = request.data
        if not self.verify_telegram_data(data):
            return Response({"error": "Invalid hash"}, status=status.HTTP_400_BAD_REQUEST)

        telegram_id = data.get('id')

        if not telegram_id:
            return Response({"error": "Telegram ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(telegram_id=telegram_id)

            refresh = RefreshToken.for_user(user)
            return Response({
                "status": "login",
                "user_id": user.id,
                "email": user.email,
                "role": user.role,
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            }, status=status.HTTP_200_OK)

        except User.DoesNotExist:

            return Response({
                "status": "registration_required",
                "telegram_data": {
                    "telegram_id": telegram_id,
                    "first_name": data.get('first_name', ''),
                    "last_name": data.get('last_name', ''),
                },
                "required_fields": ["email", "role"]
            }, status=status.HTTP_200_OK)

    def verify_telegram_data(self, data):
        if 'hash' not in data:
            return False

        auth_data = data.copy()
        hash_value = auth_data.pop('hash')

        data_check_list = []
        for key in sorted(auth_data.keys()):
            if auth_data[key] is not None:
                data_check_list.append(f"{key}={auth_data[key]}")

        data_check_string = '\n'.join(data_check_list)

        secret_key = hashlib.sha256(settings.TELEGRAM_BOT_TOKEN.encode('utf-8')).digest()
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return calculated_hash == hash_value


@extend_schema(
    summary="Регистрация пользователя Telegram",
    description="Регистрация нового пользователя, пришедшего из Telegram"
)
class TelegramRegisterView(APIView):
    @transaction.atomic
    def post(self, request):
        required_fields = ['telegram_id', 'email', 'role']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {"error": f"{field} is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        telegram_id = request.data['telegram_id']
        email = request.data['email']
        role = request.data['role']

        if User.objects.filter(telegram_id=telegram_id).exists():
            return Response(
                {"error": "User with this Telegram ID already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            telegram_id=telegram_id,
            email=email,
            role=role,
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', '')
        )

        if role == 'lessor':
            Lessor.objects.create(user=user)
        else:
            Renter.objects.create(user=user)

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "User registered successfully",
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=status.HTTP_201_CREATED)

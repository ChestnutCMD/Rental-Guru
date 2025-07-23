from datetime import datetime
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Prefetch, OuterRef, Exists, Subquery, Max
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, permissions, status, filters
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from RentalGuru import settings
from app.models import Lessor, Renter
from manager.permissions import ManagerObjectPermission
from notification.models import Notification
from payment.models import Payment
from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic, Availability, Vehicle
from .filters import MessageFilter, TripFilter, TripFilterBackend, RequestRentFilter
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, IssueSupport
from .permissions import IsAdminOrOwner, ChatsPermission
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer, \
    TopicSupportSerializer, ChatSupportSerializer, MessageSupportSerializer, IssueSupportSerializer, \
    ChatSupportRetrieveSerializer
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
from .utils import is_period_contained, subtract_periods


class BaseTripViewSet(viewsets.ModelViewSet):
    model = None

    def get_queryset(self):
        queryset = Trip.objects.all().order_by('-created_at')
        if not queryset.exists():
            return queryset

        user = self.request.user

        # Админы видят все поездки
        if user.role == 'admin':
            return queryset

        # Менеджеры с доступом к чатам видят поездки в их городе
        if hasattr(user, 'manager') and user.manager:
            manager = user.manager
            if manager.access_types.filter(name='chats').exists():
                if manager.city:
                    # Менеджер видит поездки франшиз в своем городе
                    lessor_ids = Lessor.objects.filter(franchise__city=manager.city).values_list('id', flat=True)
                    vehicle_ids = Vehicle.objects.filter(owner__lessor__id__in=lessor_ids).values_list('id', flat=True)
                    return queryset.filter(object_id__in=vehicle_ids)
                else:
                    # Менеджер без города видит все поездки
                    return queryset

        # Директор франшизы видит поездки своей франшизы
        if hasattr(user, 'franchise') and user.franchise:
            lessor_ids = Lessor.objects.filter(franchise=user.franchise).values_list('id', flat=True)
            vehicle_ids = Vehicle.objects.filter(owner__lessor__id__in=lessor_ids).values_list('id', flat=True)
            return queryset.filter(object_id__in=vehicle_ids)

        # Арендаторы видят только свои поездки
        if hasattr(user, 'renter'):
            return queryset.filter(renter=user)

        # Арендодатели видят поездки своих транспортных средств
        if hasattr(user, 'lessor'):
            content_types = [
                ContentType.objects.get_for_model(Auto),
                ContentType.objects.get_for_model(Bike),
                ContentType.objects.get_for_model(Ship),
                ContentType.objects.get_for_model(Helicopter),
                ContentType.objects.get_for_model(SpecialTechnic),
            ]
            vehicle_ids = Vehicle.objects.filter(owner=user).values_list('id', flat=True)
            return queryset.filter(content_type__in=content_types, object_id__in=vehicle_ids)

        return Trip.objects.none()


@extend_schema(summary="Поездка",
               description='Поездка',
               parameters=[
                            OpenApiParameter(
                                name="status",
                                description="Статус поездки ('current', 'started', 'finished', 'canceled')",
                                type=str,
                                enum=['current', 'started', 'finished', 'canceled'],
                                required=False,
                            ),
                            OpenApiParameter(
                                name='lessor_id', type=int,
                                description='ID арендодателя (доступно только для admin/manager)'
                            )
                           ]
               )
class TripViewSet(BaseTripViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    filter_backends = [TripFilterBackend, DjangoFilterBackend]
    filterset_class = TripFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        status = self.request.query_params.get('status')

        if status:
            queryset = queryset.filter(status=status)

        return queryset


@extend_schema(summary="Чат",
               description='Чат',
               parameters=[
                   OpenApiParameter(
                       name='lessor_id', type=int,
                       description='ID арендодателя (доступно только для admin/manager)'
                   )
               ]
               )
class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        lessor_id = self.request.query_params.get('lessor_id')

        # 1. Админы видят все чаты
        if user.role == 'admin':
            queryset = Chat.objects.all()
            if lessor_id:
                queryset = queryset.filter(
                    Q(request_rent__content_type__model='auto',
                      request_rent__object_id__in=Auto.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='bike',
                      request_rent__object_id__in=Bike.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='ship',
                      request_rent__object_id__in=Ship.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='helicopter',
                      request_rent__object_id__in=Helicopter.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='specialtechnic',
                      request_rent__object_id__in=SpecialTechnic.objects.filter(owner__lessor__id=lessor_id).values(
                          'id'))
                )

        # 2. Менеджеры с доступом к чатам
        elif hasattr(user, 'manager') and user.manager:
            manager = user.manager
            if manager.access_types.filter(name='chats').exists():
                if manager.city:
                    # Менеджер видит чаты франшиз в своем городе
                    queryset = Chat.objects.filter(
                        Q(request_rent__content_type__model='auto',
                          request_rent__object_id__in=Auto.objects.filter(owner__lessor__franchise__city=manager.city).values('id')) |
                        Q(request_rent__content_type__model='bike',
                          request_rent__object_id__in=Bike.objects.filter(owner__lessor__franchise__city=manager.city).values('id')) |
                        Q(request_rent__content_type__model='ship',
                          request_rent__object_id__in=Ship.objects.filter(owner__lessor__franchise__city=manager.city).values('id')) |
                        Q(request_rent__content_type__model='helicopter',
                          request_rent__object_id__in=Helicopter.objects.filter(owner__lessor__franchise__city=manager.city).values('id')) |
                        Q(request_rent__content_type__model='specialtechnic',
                          request_rent__object_id__in=SpecialTechnic.objects.filter(owner__lessor__franchise__city=manager.city).values('id'))
                    )
                else:
                    # Менеджер без города видит все чаты
                    queryset = Chat.objects.all()
                    
                if lessor_id:
                    queryset = queryset.filter(
                        Q(request_rent__content_type__model='auto',
                          request_rent__object_id__in=Auto.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                        Q(request_rent__content_type__model='bike',
                          request_rent__object_id__in=Bike.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                        Q(request_rent__content_type__model='ship',
                          request_rent__object_id__in=Ship.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                        Q(request_rent__content_type__model='helicopter',
                          request_rent__object_id__in=Helicopter.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                        Q(request_rent__content_type__model='specialtechnic',
                          request_rent__object_id__in=SpecialTechnic.objects.filter(owner__lessor__id=lessor_id).values('id'))
                    )
            else:
                queryset = Chat.objects.none()

        # 3. Директор франшизы видит чаты своей франшизы
        elif hasattr(user, 'franchise') and user.franchise:
            queryset = Chat.objects.filter(
                Q(request_rent__content_type__model='auto',
                  request_rent__object_id__in=Auto.objects.filter(owner__lessor__franchise=user.franchise).values(
                      'id')) |
                Q(request_rent__content_type__model='bike',
                  request_rent__object_id__in=Bike.objects.filter(owner__lessor__franchise=user.franchise).values(
                      'id')) |
                Q(request_rent__content_type__model='ship',
                  request_rent__object_id__in=Ship.objects.filter(owner__lessor__franchise=user.franchise).values(
                      'id')) |
                Q(request_rent__content_type__model='helicopter',
                  request_rent__object_id__in=Helicopter.objects.filter(owner__lessor__franchise=user.franchise).values(
                      'id')) |
                Q(request_rent__content_type__model='specialtechnic',
                  request_rent__object_id__in=SpecialTechnic.objects.filter(owner__lessor__franchise=user.franchise).values(
                      'id'))
            )

            if lessor_id:
                queryset = queryset.filter(
                    Q(request_rent__content_type__model='auto',
                      request_rent__object_id__in=Auto.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='bike',
                      request_rent__object_id__in=Bike.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='ship',
                      request_rent__object_id__in=Ship.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='helicopter',
                      request_rent__object_id__in=Helicopter.objects.filter(owner__lessor__id=lessor_id).values('id')) |
                    Q(request_rent__content_type__model='specialtechnic',
                      request_rent__object_id__in=SpecialTechnic.objects.filter(owner__lessor__id=lessor_id).values(
                          'id'))
                )

        # 4. Обычный пользователь (только его чаты)
        else:
            queryset = Chat.objects.filter(participants=user)
            
        queryset = queryset.annotate(
            last_message_timestamp=Max('messages__timestamp')
        ).order_by('-last_message_timestamp')
        return queryset.distinct()

    def get_permissions(self):
        if hasattr(self.request.user, 'manager') and self.request.user.manager:
            return [ManagerObjectPermission()]
        return super().get_permissions()


@extend_schema(summary="Сообщения", description='Сообщения')
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_class = MessageFilter

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Message.objects.all()
        if hasattr(user, 'renter') and user.renter:
            return Message.objects.filter(Q(chat__participants=user) | Q(sender=user))
        if hasattr(user, 'lessor') and user.lessor:
            return Message.objects.filter(Q(chat__participants=user) | Q(sender=user))
        if hasattr(user, 'manager') and user.manager:
            # Менеджеры видят сообщения чатов в зависимости от их доступов
            if user.manager.access_types.filter(name='chats').exists():
                return Message.objects.all()
        return Message.objects.none()


@extend_schema(summary="Заявки на аренду", description='Заявки на аренду')
class RequestRentViewSet(viewsets.ModelViewSet):
    queryset = RequestRent.objects.all()
    serializer_class = RequestRentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = RequestRentFilter

    def get_queryset(self):
        user = self.request.user
        
        optimized_queryset = RequestRent.objects.select_related(
            'vehicle_content_type',
            'organizer'
        ).prefetch_related(
            Prefetch(
                'organizer__renter',
                queryset=Renter.objects.select_related('user')
            )
        ).annotate(
            lessor_exists=Exists(
                Lessor.objects.filter(user=OuterRef('vehicle_content_object__owner'))
            ),
            lessor_id=Subquery(
                Lessor.objects.filter(user=OuterRef('vehicle_content_object__owner')).values('id')[:1]
            )
        )

        # Админы видят все заявки
        if user.role == 'admin':
            return optimized_queryset

        # Менеджеры с доступом видят заявки в своем городе
        if hasattr(user, 'manager') and user.manager:
            manager = user.manager
            if manager.access_types.filter(name='rent_orders').exists() or manager.access_types.filter(name='rent_journal').exists():
                if manager.city:
                    lessor_ids = Lessor.objects.filter(franchise__city=manager.city).values_list('id', flat=True)
                    vehicle_ids = Vehicle.objects.filter(owner__lessor__id__in=lessor_ids).values_list('id', flat=True)
                    return optimized_queryset.filter(object_id__in=vehicle_ids)
                else:
                    return optimized_queryset

        # Директор франшизы видит заявки своей франшизы
        if hasattr(user, 'franchise') and user.franchise:
            lessor_ids = Lessor.objects.filter(franchise=user.franchise).values_list('id', flat=True)
            vehicle_ids = Vehicle.objects.filter(owner__lessor__id__in=lessor_ids).values_list('id', flat=True)
            return optimized_queryset.filter(object_id__in=vehicle_ids)

        if hasattr(user, 'renter'):
            return optimized_queryset.filter(organizer=user)

        if hasattr(user, 'lessor'):
            content_types = [
                ContentType.objects.get_for_model(Auto),
                ContentType.objects.get_for_model(Bike),
                ContentType.objects.get_for_model(Ship),
                ContentType.objects.get_for_model(Helicopter),
                ContentType.objects.get_for_model(SpecialTechnic),
            ]
            vehicle_ids = Vehicle.objects.filter(owner=user).values_list('id', flat=True)
            return optimized_queryset.filter(vehicle_content_type__in=content_types, object_id__in=vehicle_ids)

        return RequestRent.objects.none()

    def check_permissions(self, request):
        user = self.request.user
        if hasattr(user, 'lessor') and request.method in ['POST']:
            raise PermissionDenied("Арендодатели не могут создавать заявки на аренду.")
        if hasattr(user, 'renter') and request.method in ['PATCH', 'PUT']:
            raise PermissionDenied("Арендаторы не могут обновлять заявки на аренду.")
        super().check_permissions(request)

    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        vehicle_type = request.data.get('vehicle_type')
        object_id = request.data.get('vehicle_id')

        if not vehicle_type:
            raise DRFValidationError("Требуется указать тип транспортного средства.")
        if not object_id:
            raise DRFValidationError("Требуется идентификатор объекта.")

        vehicle_type = vehicle_type.lower()
        model_mapping = {
            'auto': Auto,
            'bike': Bike,
            'ship': Ship,
            'helicopter': Helicopter,
            'specialtechnic': SpecialTechnic
        }

        model = model_mapping.get(vehicle_type)

        if not model:
            raise DRFValidationError(f"Недопустимый тип транспортного средства: {vehicle_type}")

        try:
            vehicle_instance = model.objects.get(id=object_id)
        except model.DoesNotExist:
            raise DRFValidationError(f"Транспортное средство с идентификатором {object_id} не существует.")

        availabilities = vehicle_instance.availabilities.all()

        # Проверка - сдается ли транспорт только верифицированным пользователям
        # if vehicle_instance.drivers_only_verified and not request.user.renter.verification:
        #     raise DRFValidationError("Транспорт сдается только верифицированным пользователям")

        # Проверка рейтинга арендатора
        if vehicle_instance.drivers_rating > Decimal(request.user.renter.get_average_rating()) and request.user.renter.get_average_rating() != 0:
            raise DRFValidationError(f"Низкий рейтинг арендатора для данного транспорта")

        if availabilities.filter(on_request=True).exists():
            request_start_date = None
            request_end_date = None
        else:
            request_start_date = request.data.get('start_date')
            request_end_date = request.data.get('end_date')

            if not request_start_date:
                raise DRFValidationError("Обязательна дата начала.")
            if not request_end_date:
                raise DRFValidationError("Обязательна дата окончания.")

            # Преобразование строк в объекты даты
            if isinstance(request_start_date, str):
                request_start_date = datetime.strptime(request_start_date, '%Y-%m-%d').date()
            if isinstance(request_end_date, str):
                request_end_date = datetime.strptime(request_end_date, '%Y-%m-%d').date()

            # Преобразование дат в строки перед передачей в is_period_contained
            sub_period = {
                'start_date': request_start_date.strftime('%Y-%m-%d'),
                'end_date': request_end_date.strftime('%Y-%m-%d')
            }

            # Проверка доступных дат
            availabilities_dates = [
                {
                    'start_date': availability.start_date.strftime('%Y-%m-%d'),
                    'end_date': availability.end_date.strftime('%Y-%m-%d')
                }
                for availability in availabilities
            ]

            if not is_period_contained(availabilities_dates, sub_period):
                raise DRFValidationError("Запрашиваемый период недоступен для данного транспортного средства.")

            # Проверка на минимальное и максимальное количество дней аренды
            rental_days = (request_end_date - request_start_date).days + 1
            min_days = vehicle_instance.min_rent_day
            max_days = vehicle_instance.max_rent_day

            if rental_days < min_days or rental_days > max_days:
                warning_message = (
                    f"Период аренды должен быть между {min_days} и {max_days} днями. "
                    f"Текущий период: {rental_days} дней."
                )
                return Response({'warning': warning_message}, status=status.HTTP_400_BAD_REQUEST)

        # Создание записи аренды после всех проверок
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_rent = serializer.save()

        # Отправка уведомлений
        url = f'{settings.HOST_URL}/chat/request_rents/{request_rent.id}'
        content = f'Вам поступила заявка на аренду {vehicle_instance}'
        Notification.objects.create(user=vehicle_instance.owner, content=content, url=url)

        response_data = serializer.data

        if request_rent.on_request:
            chat = Chat.objects.filter(request_rent=request_rent).first()
            if chat:
                response_data['chat_id'] = chat.id

        return Response(response_data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        instance = self.get_object()
        if 'status' in self.request.data:
            new_status = self.request.data['status']

            if new_status not in ['denied', 'accept', 'unknown']:
                raise DRFValidationError("Недопустимый статус.")

            # Обработка отказа заявки
            if new_status == 'denied':
                if instance.owner != self.request.user:
                    raise DRFValidationError("Только владелец транспортного средства может отклонить запрос.")
                denied_reason = self.request.data.get('denied_reason')
                if not denied_reason:
                    raise DRFValidationError("Причина отказа обязательна, если статус заявки — 'denied'.")
                content = f'Вам отказано в аренде транспорта {instance.vehicle} по причине: {denied_reason}'
                url = ''
                Notification.objects.create(user=instance.organizer, content=content, url=url)
                serializer.save(user=self.request.user)

            # Обработка принятия заявки
            if new_status == 'accept':
                if instance.owner != self.request.user:
                    raise DRFValidationError("Только владелец транспортного средства может принять запрос.")

                model = instance.content_type.model_class()
                object_id = instance.object_id
                try:
                    vehicle_instance = model.objects.get(id=object_id)
                except model.DoesNotExist:
                    raise DRFValidationError(f"Транспорт с ID {object_id} не найден.")

                availabilities = list(vehicle_instance.availabilities.values('start_date', 'end_date'))
                if not availabilities:
                    raise DRFValidationError("Данных о наличии свободных периодов аренды для этого транспорта не найдено.")

                # Преобразование дат в строки
                for availability in availabilities:
                    availability['start_date'] = availability['start_date'].strftime('%Y-%m-%d')
                    availability['end_date'] = availability['end_date'].strftime('%Y-%m-%d')

                sub_period = {'start_date': instance.start_date.strftime('%Y-%m-%d'),
                              'end_date': instance.end_date.strftime('%Y-%m-%d')}
                new_availabilities = subtract_periods(availabilities, sub_period)

                if isinstance(new_availabilities, str):
                    raise DRFValidationError(new_availabilities)

                # Обновление или создание новых объектов Availability
                vehicle_instance.availabilities.all().delete()
                for availability in new_availabilities:
                    Availability.objects.create(
                        vehicle=vehicle_instance,
                        start_date=availability['start_date'],
                        end_date=availability['end_date']
                    )

                # Здесь Trip будет создан в модели RequestRent
                serializer.save(user=self.request.user)

                url = f'{settings.HOST_URL}/chat/request_rents/{instance.id}'
                content = f'Заявка на аренду {vehicle_instance} одобрена. Дата начала {instance.start_date}'
                Notification.objects.create(user=instance.organizer, content=content, url=url)
        else:
            serializer.save(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save()
        return Response({'detail': 'Заявка удалена.'}, status=status.HTTP_204_NO_CONTENT)


class CustomLimitOffsetPagination(LimitOffsetPagination):
    default_limit = 10
    limit_query_param = 'limit'
    offset_query_param = 'offset'


class ChatSupportPagination(LimitOffsetPagination):
    default_limit = 20
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100


@extend_schema(summary="Темы обращений в техподдержку", description="Темы обращений в техподдержку")
class TopicSupportViewSet(viewsets.ModelViewSet):
    queryset = TopicSupport.objects.all()
    serializer_class = TopicSupportSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(summary="Список чатов техподдержки", description="""\nЧат с техподдержкой. Доступен по адресу:\n
                    wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT>&lang=<lang>\n
                    Получение предыдущих сообщений: {"type": "load_previous_messages", "offset": 20, "limit": 10}
                    Отправка сообщения: {"type": "send_message", "message": "hello"}
                    Обновление сообщения: {"type": "update_message", "update": 74, "content": "Hello" }
                    Удаление сообщения: {"type": "delete_message", "delete": 74}
                    Отправка сообщения с файлом: {"type": "send_message", 
                                                  "message": {
                                                              "content": "Hello!",
                                                              "file": "data:image/jpeg;base64,/9j/4AAQS..."
                                                              "name": "example.jpg"                                                              
                                                             }
                                                  }
                    """)
class ChatSupportListView(APIView):
    permission_classes = [ChatsPermission]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role in ['admin', 'manager']:
            chats = ChatSupport.objects.select_related(
                                                        'creator',
                                                        'creator__lessor',
                                                        'creator__renter',
                                                        'creator__influencer',
                                                        'creator__franchise'
                                                    ).all()
            paginator = ChatSupportPagination()
            paginated_chats = paginator.paginate_queryset(chats, request)
            if paginated_chats is None:
                return Response({"detail": "На этой странице нет доступных чатов."}, status=status.HTTP_404_NOT_FOUND)
            serializer = ChatSupportSerializer(paginated_chats, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)
        else:
            chats = ChatSupport.objects.select_related(
                                                        'creator',
                                                        'creator__lessor',
                                                        'creator__renter',
                                                        'creator__influencer',
                                                        'creator__franchise'
                                                    ).filter(creator=user)
            serializer = ChatSupportSerializer(chats, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(summary="Детальное отображение чата", description="""\nЧат с техподдержкой. Доступен по адресу:\n
                    wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT>&lang=<lang>\n
                    Получение предыдущих сообщений: {"type": "load_previous_messages", "offset": 20, "limit": 10}
                    Отправка сообщения: {"type": "send_message", "message": "hello"}
                    Обновление сообщения: {"type": "update_message", "update": 74, "content": "Hello" }
                    Удаление сообщения: {"type": "delete_message", "delete": 74}
                    Отправка сообщения с файлом: {"type": "send_message", 
                                                  "message": {
                                                              "content": "Hello!",
                                                              "file": "data:image/jpeg;base64,/9j/4AAQS..."
                                                              "name": "example.jpg"                                                              
                                                             }
                                                  }
                    """)
class ChatSupportRetrieveView(APIView):
    permission_classes = [ChatsPermission]

    def get(self, request, pk, *args, **kwargs):
        try:
            chat = ChatSupport.objects.get(pk=pk)
            if request.user.role not in ['admin', 'manager'] and chat.creator != request.user:
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = ChatSupportRetrieveSerializer(chat)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ChatSupport.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)


@extend_schema(summary="Обращение в техподдержку", description="""\nЧат с техподдержкой. Доступен по адресу:\n
                    wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT>&lang=<lang>\n
                    Получение предыдущих сообщений: {"type": "load_previous_messages", "offset": 20, "limit": 10}
                    Отправка сообщения: {"type": "send_message", "message": "hello"}
                    Обновление сообщения: {"type": "update_message", "update": 74, "content": "Hello" }
                    Удаление сообщения: {"type": "delete_message", "delete": 74}
                    Отправка сообщения с файлом: {"type": "send_message", 
                                                  "message": {
                                                              "content": "Hello!",
                                                              "file": "data:image/jpeg;base64,/9j/4AAQS..."
                                                              "name": "example.jpg"                                                              
                                                             }
                                                  }                
                    """)
class IssueSupportViewSet(viewsets.ModelViewSet):
    queryset = IssueSupport.objects.all()
    serializer_class = IssueSupportSerializer
    permission_classes = [ChatsPermission]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager']:
            return IssueSupport.objects.all()
        return IssueSupport.objects.filter(chat__creator=user)


@extend_schema(summary="Сообщения чата техподдержки", description="Сообщения чата техподдержки")
class MessageSupportViewSet(viewsets.ModelViewSet):
    queryset = MessageSupport.objects.all()
    serializer_class = MessageSupportSerializer
    permission_classes = [ChatsPermission]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)


@extend_schema(summary="Количество непрочитанных сообщений",
            description="Возвращает количество непрочитанных сообщений во всех чатах пользователя, включая чат техподдержки.",
            responses={200: {'application/json': {'example': {'unread_messages': 5}}}}
    )
class UnreadMessagesCountAPIView(APIView):
    def get(self, request, *args, **kwargs):
        user = request.user

        user_chats = Chat.objects.filter(participants=user).values_list('id', flat=True)

        unread_in_chats = (Message.objects.filter(chat_id__in=user_chats, is_read=False, deleted=False)
                            .exclude(sender=user).count())

        chat_support = (ChatSupport.objects.filter(creator=user).values_list('id', flat=True).first())

        unread_in_support = 0
        if chat_support:
            unread_in_support = (MessageSupport.objects.filter(chat_id=chat_support, is_read=False, deleted=False)
                                .exclude(sender=user).count())

        total_unread = unread_in_chats + unread_in_support

        return Response({'unread_messages': total_unread}, status=status.HTTP_200_OK)
from datetime import datetime
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, permissions, status, filters
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from RentalGuru import settings
from manager.permissions import ManagerObjectPermission
from notification.models import Notification
from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic, Availability
from .filters import MessageFilter
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, IssueSupport
from .permissions import IsAdminOrOwner
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer, \
    TopicSupportSerializer, ChatSupportSerializer, MessageSupportSerializer, IssueSupportSerializer, \
    ChatSupportRetrieveSerializer
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
from .utils import is_period_contained, subtract_periods


@extend_schema(summary="Поездка", description='Поездка')
class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        auto_content_type = ContentType.objects.get_for_model(Auto)
        bike_content_type = ContentType.objects.get_for_model(Bike)
        ship_content_type = ContentType.objects.get_for_model(Ship)
        helicopter_content_type = ContentType.objects.get_for_model(Helicopter)
        special_technic_content_type = ContentType.objects.get_for_model(SpecialTechnic)

        return Trip.objects.filter(Q(organizer=user) |
                                   Q(content_type=auto_content_type,
                                     object_id__in=Auto.objects.filter(owner=user).values('id')) |
                                   Q(content_type=bike_content_type,
                                     object_id__in=Bike.objects.filter(owner=user).values('id')) |
                                   Q(content_type=ship_content_type,
                                     object_id__in=Ship.objects.filter(owner=user).values('id')) |
                                   Q(content_type=helicopter_content_type,
                                     object_id__in=Helicopter.objects.filter(owner=user).values('id')) |
                                   Q(content_type=special_technic_content_type,
                                     object_id__in=SpecialTechnic.objects.filter(owner=user).values('id')))


@extend_schema(summary="Чат между арендатором и арендодателем", description="""\nЧат между арендатором и арендодателем. 
                                                                                Создается автоматически при создании 
                                                                                заявки на аренду с открытой датой, либо 
                                                                                при принятии заявки на аренду 
                                                                                арендодателем. Чат доступен по адресу:\n 
                    wss://<host_name>/ws/chat/<chat_id>/?token=<JWT>&lang=<lang>\n
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
                        
                        Обновление заявки со стороны арендодателя: {
                                                                    "update_request_rent": {
                                                                        "content_type": "Auto",
                                                                        "object_id": 7,
                                                                        "start_time": "09:00",
                                                                        "end_time": "18:00",
                                                                        "start_date": "2024-11-01",
                                                                        "end_date": "2024-11-10",
                                                                        "total_cost": "500.00"
                                                                        }
                                                                    }
                        Обновление статуса заявки со стороны арендатора: {
                                                                          "update_status": {
                                                                             "status": "accept"
                                                                             }
                                                                        }""")
class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user)

    def get_permissions(self):
        if hasattr(self.request.user, 'manager') and self.request.user.manager:
            return [ManagerObjectPermission]
        return super().get_permissions()

@extend_schema(summary="Сообщения чата арендодателя и арендатора", description="Сообщения чата арендодателя и "
                                                                               "арендатора")
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MessageFilter
    ordering_fields = ['timestamp']

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(chat__participants=user)


@extend_schema(summary="Заявка на аренду", description="Заявка на аренду. Создать может только пользователь renter.\
                                                После создания пользователь, который является владельцем транспорта,\
                                                может обновить статус заявки - принять или отклонить (accept|denied).\
                                                При изменении статуса на accept автоматически создается поездка Trip)")
class RequestRentViewSet(viewsets.ModelViewSet):
    serializer_class = RequestRentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        content_types = {
            'Auto': ContentType.objects.get_for_model(Auto),
            'Bike': ContentType.objects.get_for_model(Bike),
            'Ship': ContentType.objects.get_for_model(Ship),
            'Helicopter': ContentType.objects.get_for_model(Helicopter),
            'SpecialTechnic': ContentType.objects.get_for_model(SpecialTechnic)
        }

        filters = Q(organizer=user)
        for model_name, content_type in content_types.items():
            model = content_type.model_class()
            filters |= Q(content_type=content_type, object_id__in=model.objects.filter(owner=user).values('id'))

        return RequestRent.objects.filter(filters, is_deleted=False)

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

        return Response(serializer.data, status=status.HTTP_201_CREATED)

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


@extend_schema(summary="Тема чата с техподдержкой", description="Тема чата с техподдержкой")
class TopicSupportViewSet(viewsets.ModelViewSet):
    queryset = TopicSupport.objects.all()
    serializer_class = TopicSupportSerializer
    permissions = [IsAuthenticated]


class ChatSupportPagination(LimitOffsetPagination):
    default_limit = 10
    max_limit = 100


@extend_schema(summary="Список чатов техподдержки",
               parameters=[
                            OpenApiParameter(
                                name="limit",
                                description="Количество объектов на странице",
                                required=False,
                                type=int
                            ),
                            OpenApiParameter(
                                name="offset",
                                description="Начальная позиция (смещение)",
                                required=False,
                                type=int
                            ),
                        ],

               description="""\nЧат с техподдержкой. Доступен по адресу:\n
                    wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT>&lang=<lang>\n
                    Чат создается при создании обращения\n
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
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.role in ['admin', 'manager']:
            chats = ChatSupport.objects.all()
            paginator = ChatSupportPagination()
            paginated_chats = paginator.paginate_queryset(chats, request)
            if paginated_chats is None:
                return Response({"detail": "На этой странице нет доступных чатов."}, status=status.HTTP_404_NOT_FOUND)
            serializer = ChatSupportSerializer(paginated_chats, many=True)
            return paginator.get_paginated_response(serializer.data)
        else:
            chats = ChatSupport.objects.filter(creator=user)
            serializer = ChatSupportSerializer(chats, many=True)
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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'manager']:
            return IssueSupport.objects.all()
        return IssueSupport.objects.filter(chat__creator=user)


@extend_schema(summary="Сообщения чата техподдержки", description="Сообщения чата техподдержки")
class MessageSupportViewSet(viewsets.ModelViewSet):
    queryset = MessageSupport.objects.all()
    serializer_class = MessageSupportSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

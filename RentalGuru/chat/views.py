import os
import redis
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from RentalGuru import settings
from notification.models import Notification
from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic, Availability
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, Feedback
from .permissions import IsAdminOrOwner, IsParticipantOrAdmin, IsChatCreatorOrAdmin
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer, \
    TopicSupportSerializer, ChatSupportSerializer, MessageSupportSerializer, FeedbackUpdateSerializer, \
    FeedbackSerializer, FeedbackCreateSerializer
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied
from .utils import is_period_contained, subtract_periods, calculate_age


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


@extend_schema(summary="Чат между арендатором и арендодателем", description='Чат между арендатором и арендодателем. '
                                                                            'Создается автоматически при создании '
                                                                            'поездки. Чат доступен по адресу '
                                                                            'wss://<host_name>/ws/chat/<chat_id'
                                                                            '>/?token=<JWT>&lang=<lang>')
class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user)


@extend_schema(summary="Сообщения чата арендодателя и арендатора", description="Сообщения чата арендодателя и "
                                                                               "арендатора")
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(chat__participants=user)


def check_redis(request):
    """ Проверка redis """
    try:
        r = redis.Redis(host=os.getenv('REDIS_HOST'), port=6379, db=0)
        r.ping()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


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

        return RequestRent.objects.filter(filters)

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
        request_start_date = request.data.get('start_date')
        request_end_date = request.data.get('end_date')

        if not vehicle_type:
            raise DRFValidationError("Требуется указать тип транспортного средства.")
        if not object_id:
            raise DRFValidationError("Требуется идентификатор объекта.")
        if not request_start_date:
            raise DRFValidationError("Обязательна дата начала.")
        if not request_end_date:
            raise DRFValidationError("Обязательна дата окончания.")

        vehicle_type = vehicle_type.lower()  # Преобразуем к нижнему регистру для сравнения
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

        availabilities = list(vehicle_instance.availabilities.values('start_date', 'end_date'))
        if not availabilities:
            raise DRFValidationError("Не найдено доступных дат для этого транспорта.")

        # Преобразование дат в строки
        for availability in availabilities:
            availability['start_date'] = availability['start_date'].strftime('%Y-%m-%d')
            availability['end_date'] = availability['end_date'].strftime('%Y-%m-%d')

        sub_period = {'start_date': request_start_date, 'end_date': request_end_date}

        if not is_period_contained(availabilities, sub_period):
            raise DRFValidationError("Запрашиваемый период недоступен для данного транспортного средства.")

        user_age = calculate_age(request.user.date_of_birth)
        drivers_age = vehicle_instance.drivers_age

        if request.user.date_of_birth is None or user_age < drivers_age:
            raise DRFValidationError("Пользователь не соответствует возрастным требованиям, предъявляемым к данному транспортному средству.")

        if vehicle_instance.drivers_only_verified and not request.user.renter.verification:
            raise DRFValidationError("Транспорт сдается только верифицированным пользователям")

        if vehicle_instance.drivers_rating > request.user.renter.get_average_rating():
            raise DRFValidationError(f"Требуемый рейтинг для аренды транспорта: {vehicle_instance.drivers_rating}")

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
            if new_status == 'accept':
                if instance.owner != self.request.user:
                    raise DRFValidationError("Only the vehicle owner can accept the request.")

                model = instance.content_type.model_class()
                object_id = instance.object_id
                try:
                    vehicle_instance = model.objects.get(id=object_id)
                except model.DoesNotExist:
                    raise DRFValidationError(f"Vehicle with ID {object_id} does not exist.")

                availabilities = list(vehicle_instance.availabilities.values('start_date', 'end_date'))
                if not availabilities:
                    raise DRFValidationError("No availability data found for this vehicle.")

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

                Trip.objects.create(
                    organizer=instance.organizer,
                    content_type=instance.content_type,
                    object_id=instance.object_id,
                    start_date=instance.start_date,
                    end_date=instance.end_date
                )

                url = f'{settings.HOST_URL}/chat/request_rents/{instance.id}'
                content = f'Заявка на аренду {vehicle_instance} одобрена. Дата начала {instance.start_date}'
                Notification.objects.create(user=instance.organizer, content=content, url=url)
        serializer.save(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().update(request, *args, **kwargs)


# Чат с техподдержкой


@extend_schema(summary="Тема чата с техподдержкой", description="Тема чата с техподдержкой")
class TopicSupportViewSet(viewsets.ModelViewSet):
    queryset = TopicSupport.objects.all()
    serializer_class = TopicSupportSerializer
    permissions = [IsAuthenticated]


@extend_schema(summary="Чат с техподдержкой", description="Чат с техподдержкой. Доступен по адресу "
                                                          "wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT"
                                                          ">&lang=<lang>")
class ChatSupportViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSupportSerializer
    permission_classes = [IsChatCreatorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            if user.role == 'admin':
                return ChatSupport.objects.all()
            else:
                return ChatSupport.objects.filter(creator=user)
        else:
            return ChatSupport.objects.none()

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        # Для вывода сообщений используем связанный ресурс message_support внутри сериализатора
        serializer = self.get_serializer(instance)
        data = serializer.data

        # Добавляем все сообщения данного чата
        messages = MessageSupport.objects.filter(support_chat=instance)
        message_serializer = MessageSupportSerializer(messages, many=True)
        data['messages'] = message_serializer.data

        # Добавляем название темы
        data['topic_name'] = instance.topic.name if instance.topic else None
        return Response(data)


@extend_schema(summary="Сообщения чата техподдержки", description="Сообщения чата техподдержки")
class MessageSupportViewSet(viewsets.ModelViewSet):
    queryset = MessageSupport.objects.all()
    serializer_class = MessageSupportSerializer
    permission_classes = [IsParticipantOrAdmin]

    def create(self, request, *args, **kwargs):
        chat = self.get_object()
        content = request.data.get('content')
        message = MessageSupport.objects.create(support_chat=chat, sender=request.user, content=content)
        serializer = MessageSupportSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(summary="Отзывы", description="Отзывы к транспорту может оставлять только пользователь, который "
                                             "пользовался транспортом, только после завершения поездки и только один "
                                             "отзыв к одному транспорту. Отвечать на отзывы может только хозяин "
                                             "транспорта")
class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('user', 'content_type').all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create']:
            return FeedbackCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FeedbackUpdateSerializer
        return FeedbackSerializer

    def perform_create(self, serializer):
        content_type_id = self.request.data.get('content_type')
        object_id = self.request.data.get('object_id')

        if not content_type_id or not object_id:
            raise serializers.ValidationError("Необходимо указать content_type и object_id.")

        try:
            content_type = ContentType.objects.get(id=content_type_id)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError("Указанный тип контента не существует.")

        # Проверка, оставлял ли уже пользователь отзыв для данного транспортного средства
        existing_feedback = Feedback.objects.filter(
            user=self.request.user,
            content_type=content_type,
            object_id=object_id
        ).exists()

        if existing_feedback:
            raise serializers.ValidationError("Вы уже оставили отзыв для данного транспортного средства.")

        try:
            trip = Trip.objects.get(
                organizer=self.request.user,
                content_type=content_type,
                object_id=object_id
            )
        except Trip.DoesNotExist:
            raise serializers.ValidationError(
                "Для того чтобы оставить отзыв, нужно воспользоваться данным транспортом.")

        if trip.end_date > timezone.now().date():
            raise serializers.ValidationError("Поездка еще не завершена.")

        # Получение экземпляра транспортного средства
        vehicle_instance = content_type.get_object_for_this_type(id=object_id)

        serializer.save(user=self.request.user, content_type=content_type, object_id=object_id)

        # Отправка уведомлений
        content = f'Добавлен отзыв для транспорта {content_type.model}'
        url = f'{settings.HOST_URL}/chat/feedbacks/{object_id}'
        Notification.objects.create(user=vehicle_instance.owner, content=content, url=url)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if 'answer' in request.data:
            if instance.vehicle.owner != request.user:
                raise serializers.ValidationError("Только владелец транспорта может оставлять ответы на отзывы.")
            instance.answer = request.data['answer']
            instance.save()
            return Response(FeedbackSerializer(instance).data)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

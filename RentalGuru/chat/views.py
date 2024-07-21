import redis
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport
from .permissions import IsAdminOrOwner, IsParticipantOrAdmin, IsChatCreatorOrAdmin
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer, \
    TopicSupportSerializer, ChatSupportSerializer, MessageSupportSerializer
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied


@extend_schema(summary="Поездка", description='Поездка')
class TripViewSet(viewsets.ModelViewSet):
    """ Поездка """
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
            Q(content_type=auto_content_type, object_id__in=Auto.objects.filter(owner=user).values('id')) |
            Q(content_type=bike_content_type, object_id__in=Bike.objects.filter(owner=user).values('id')) |
            Q(content_type=ship_content_type, object_id__in=Ship.objects.filter(owner=user).values('id')) |
            Q(content_type=helicopter_content_type, object_id__in=Helicopter.objects.filter(owner=user).values('id')) |
            Q(content_type=special_technic_content_type, object_id__in=SpecialTechnic.objects.filter(owner=user).values('id')))


@extend_schema(summary="Чат между арендатором и арендодателем", description='Чат между арендатором и арендодателем. '
                                                                            'Создается автоматически при создании '
                                                                            'поездки. Чат доступен по адресу '
                                                                            'wss://<host_name>/ws/chat/<chat_id>/?token=<JWT>')
class ChatViewSet(viewsets.ModelViewSet):
    """ Чат между арендатором и арендодателем. Создается автоматически при создании поездки """
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user)


@extend_schema(summary="Сообщения чата арендодателя и арендатора", description="Сообщения чата арендодателя и "
                                                                               "арендатора")
class MessageViewSet(viewsets.ModelViewSet):
    """ Сообщения чата арендодателя и арендатора """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(chat__participants=user)


def check_redis(request):
    """ Проверка redis """
    try:
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.ping()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@extend_schema(summary="Заявка на аренду", description="Заявка на аренду. Создать может только пользователь renter.\
                                                После создания пользователь, который является владельцем транспорта,\
                                                может обновить статус заявки - принять или отклонить (accept|denied).\
                                                При изменении статуса на denied автоматически создается поездка Trip)")
class RequestRentViewSet(viewsets.ModelViewSet):
    """ Заявка на аренду. Создать может только пользователь renter.
    После создания пользователь, который является владельцем транспорта,
    может обновить статус заявки - принять или отклонить (accept|denied).
    При изменении статуса на denied автоматически создается поездка Trip)
    """
    serializer_class = RequestRentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        content_types = {
            Auto: ContentType.objects.get_for_model(Auto),
            Bike: ContentType.objects.get_for_model(Bike),
            Ship: ContentType.objects.get_for_model(Ship),
            Helicopter: ContentType.objects.get_for_model(Helicopter),
            SpecialTechnic: ContentType.objects.get_for_model(SpecialTechnic)
        }

        filters = Q(organizer=user)
        for model, content_type in content_types.items():
            filters |= Q(content_type=content_type, object_id__in=model.objects.filter(owner=user).values('id'))

        return RequestRent.objects.filter(filters)

    def check_permissions(self, request):
        user = request.user
        if hasattr(user, 'lessor') and request.method in ['POST']:
            raise PermissionDenied("Арендодатели не могут создавать заявки на аренду.")
        if hasattr(user, 'renter') and request.method in ['PATCH', 'PUT']:
            raise PermissionDenied("Арендаторы не могут обновлять заявки на аренду.")
        super().check_permissions(request)

    def perform_update(self, serializer):
        instance = self.get_object()
        if 'status' in self.request.data:
            new_status = self.request.data['status']
            if new_status == 'accept':
                if instance.owner != self.request.user:
                    raise DRFValidationError("Только владелец транспортного средства может принять запрос.")
                Trip.objects.create(
                    organizer=instance.organizer,
                    content_type=instance.content_type,
                    object_id=instance.object_id,
                    start_date=instance.start_date,
                    end_date=instance.end_date
                )
        serializer.save(user=self.request.user)

    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().create(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().update(request, *args, **kwargs)


# Чат с техподдержкой

@extend_schema(summary="Тема чата с техподдержкой", description="Тема чата с техподдержкой")
class TopicSupportViewSet(viewsets.ModelViewSet):
    """ Тема чата с техподдержкой """
    queryset = TopicSupport.objects.all()
    serializer_class = TopicSupportSerializer
    permissions = [IsAuthenticated]


@extend_schema(summary="Чат с техподдержкой", description="Чат с техподдержкой. Доступен по адресу "
                                                          "wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT>")
class ChatSupportViewSet(viewsets.ModelViewSet):
    """ Чат с техподдержкой """
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
    """ Сообщения чата техподдержки """
    queryset = MessageSupport.objects.all()
    serializer_class = MessageSupportSerializer
    permission_classes = [IsParticipantOrAdmin]

    def create(self, request, *args, **kwargs):
        chat = self.get_object()
        content = request.data.get('content')
        message = MessageSupport.objects.create(support_chat=chat, sender=request.user, content=content)
        serializer = MessageSupportSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
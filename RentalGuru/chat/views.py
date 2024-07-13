import redis
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import viewsets, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport
from .permissions import IsAdminOrOwner, IsParticipantOrAdmin, IsChatCreatorOrAdmin
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer, \
    TopicSupportSerializer, ChatSupportSerializer, MessageSupportSerializer
from rest_framework.exceptions import ValidationError as DRFValidationError


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Trip.objects.filter(Q(organizer=user) | Q(vehicle__owner=user))


class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    queryset = Chat.objects.all()

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    queryset = Message.objects.all()

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(chat__participants=user)


def check_redis(request):
    try:
        r = redis.Redis(host='127.0.0.1', port=6379, db=0)
        r.ping()
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


class RequestRentViewSet(viewsets.ModelViewSet):
    queryset = RequestRent.objects.all()
    serializer_class = RequestRentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return RequestRent.objects.filter(Q(organizer=user) | Q(vehicle__owner=user))

    def perform_update(self, serializer):
        instance = self.get_object()
        if 'status' in self.request.data and self.request.data['status'] == 'accept':
            if instance.owner != self.request.user:
                raise DRFValidationError("Только владелец транспортного средства может принять запрос.")
        serializer.save(user=self.request.user)


# Чат с техподдержкой


class TopicSupportViewSet(viewsets.ModelViewSet):
    queryset = TopicSupport.objects.all()
    serializer_class = TopicSupportSerializer
    permissions = [IsAuthenticated]


class ChatSupportViewSet(viewsets.ModelViewSet):
    queryset = ChatSupport.objects.all()
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

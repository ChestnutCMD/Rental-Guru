from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Trip, Chat, Message
from .serializers import TripSerializer, ChatSerializer, MessageSerializer
from django.contrib.contenttypes.models import ContentType
from .permissions import IsAdminOrOwner


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Trip.objects.all()
        return Trip.objects.filter(renter=user)

    def create(self, request, *args, **kwargs):
        # Извлечение данных из запроса
        vehicle_type = request.data.get('vehicle_type')
        vehicle_id = request.data.get('vehicle_id')
        renter_id = request.data.get('renter_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        # Получение типа контента для транспортного средства
        content_type = ContentType.objects.get(model=vehicle_type)

        # Создание поездки
        trip = Trip.objects.create(
            content_type=content_type,
            object_id=vehicle_id,
            renter_id=renter_id,
            start_date=start_date,
            end_date=end_date
        )

        # Создание чата
        vehicle_instance = content_type.get_object_for_this_type(id=vehicle_id)
        chat = Chat.objects.create(trip=trip)
        chat.participants.add(vehicle_instance.owner, trip.renter)

        return Response({
            'trip': TripSerializer(trip).data,
            'chat': ChatSerializer(chat).data
        }, status=status.HTTP_201_CREATED)


class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Chat.objects.all()
        return Chat.objects.filter(participants=user)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return Message.objects.all()
        return Message.objects.filter(chat__participants=user)

    @action(detail=False, methods=['post'])
    def send_message(self, request, *args, **kwargs):
        chat_id = request.data.get('chat_id')
        content = request.data.get('content')
        chat = Chat.objects.get(id=chat_id)
        message = Message.objects.create(chat=chat, sender=request.user, content=content)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

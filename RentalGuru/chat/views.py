import redis
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from .models import Trip, Chat, Message, RequestRent
from .permissions import IsAdminOrOwner
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer
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
    queryset = Chat.objects.all()  # Добавьте этот атрибут

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    queryset = Message.objects.all()  # Добавьте этот атрибут

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

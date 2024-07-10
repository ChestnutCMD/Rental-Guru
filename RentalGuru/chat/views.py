from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Trip, Chat, Message
from .permissions import IsAdminOrOwner
from .serializers import TripSerializer, ChatSerializer, MessageSerializer


class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]


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

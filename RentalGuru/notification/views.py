import os

from django.http import FileResponse
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from RentalGuru import settings
from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('user')

    @action(detail=True, methods=['get'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.read_it = True
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)


def get_fcm_token(request):
    return render(request, 'test_push.html')


def firebase_messaging_sw(request):
    path = os.path.join(settings.STATIC_ROOT, 'firebase-messaging-sw.js')
    return FileResponse(open(path, 'rb'), content_type='application/javascript')

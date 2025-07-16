import logging
import os

from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from RentalGuru import settings
from .models import Notification
from .permissions import IsAdminOrOwner, IsAdmin
from .serializers import NotificationSerializer


@extend_schema(summary="Уведомления", description="CRUD уведомлений")
class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsAdminOrOwner]
        elif self.action in ['create', 'update', 'partial_update']:
            self.permission_classes = [IsAuthenticated, IsAdmin]
        return super().get_permissions()

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).select_related('user').order_by('-created_at')

    @action(detail=True, methods=['get'])
    def read(self, request, pk=None):
        notification = self.get_object()
        notification.read_it = True
        notification.save()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)


@extend_schema(summary="FCM токен", description="FCM токен")
def get_fcm_token(request):
    return render(request, 'test_push.html')


def firebase_messaging_sw(request):
    path = os.path.join(settings.STATIC_ROOT, 'firebase-messaging-sw.js')
    return FileResponse(open(path, 'rb'), content_type='application/javascript')
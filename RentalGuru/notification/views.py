import os

from django.http import FileResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
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


@cache_control(max_age=3600)
def firebase_messaging_sw(request):
    """
    Обслуживание Service Worker для Firebase
    """
    try:
        path = os.path.join(settings.STATIC_ROOT, 'firebase-messaging-sw.js')
        if os.path.exists(path):
            response = FileResponse(
                open(path, 'rb'),
                content_type='application/javascript'
            )
            # Добавляем заголовки для Service Worker
            response['Service-Worker-Allowed'] = '/'
            response['Cache-Control'] = 'max-age=3600'
            return response
        else:
            # Если файл не найден, возвращаем 404
            return HttpResponse(
                "Service Worker file not found",
                status=404,
                content_type='text/plain'
            )
    except Exception as e:
        return HttpResponse(
            f"Error serving Service Worker: {str(e)}",
            status=500,
            content_type='text/plain'
        )
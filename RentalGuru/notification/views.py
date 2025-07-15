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


logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
@cache_control(max_age=0, must_revalidate=True)
def firebase_messaging_sw(request):
    """
    Обслуживание Service Worker для Firebase
    """
    try:
        possible_paths = [
            os.path.join(settings.STATIC_ROOT, 'firebase-messaging-sw.js'),
            os.path.join(settings.BASE_DIR, 'static', 'firebase-messaging-sw.js'),
            os.path.join(settings.BASE_DIR, 'staticfiles', 'firebase-messaging-sw.js'),
        ]

        sw_path = None
        for path in possible_paths:
            if os.path.exists(path):
                sw_path = path
                break

        if sw_path:
            logger.info(f"Service Worker найден по пути: {sw_path}")

            with open(sw_path, 'rb') as f:
                content = f.read()

            response = HttpResponse(content, content_type='application/javascript')

            response['Service-Worker-Allowed'] = '/'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            if hasattr(settings, 'CORS_ALLOW_ALL_ORIGINS') and settings.CORS_ALLOW_ALL_ORIGINS:
                response['Access-Control-Allow-Origin'] = '*'

            return response
        else:
            logger.error(f"Service Worker не найден. Проверенные пути: {possible_paths}")

            fallback_sw = """
// Fallback Service Worker
console.log('Fallback Service Worker загружен');

self.addEventListener('install', function(event) {
    console.log('Fallback Service Worker установлен');
    event.waitUntil(self.skipWaiting());
});

self.addEventListener('activate', function(event) {
    console.log('Fallback Service Worker активирован');
    event.waitUntil(self.clients.claim());
});
"""
            response = HttpResponse(fallback_sw, content_type='application/javascript')
            response['Service-Worker-Allowed'] = '/'
            response['Cache-Control'] = 'no-cache'
            return response

    except Exception as e:
        logger.error(f"Ошибка при обслуживании Service Worker: {str(e)}")

        error_sw = f"""
// Error Service Worker
console.error('Ошибка загрузки Service Worker: {str(e)}');

self.addEventListener('install', function(event) {{
    console.log('Error Service Worker установлен');
    event.waitUntil(self.skipWaiting());
}});

self.addEventListener('activate', function(event) {{
    console.log('Error Service Worker активирован');
    event.waitUntil(self.clients.claim());
}});
"""
        response = HttpResponse(error_sw, content_type='application/javascript')
        response['Service-Worker-Allowed'] = '/'
        response['Cache-Control'] = 'no-cache'
        return response


@csrf_exempt
@require_http_methods(["GET"])
def fcm_debug(request):
    """
    Отладочная информация для FCM
    """
    debug_info = {
        'static_root': getattr(settings, 'STATIC_ROOT', 'Not set'),
        'base_dir': getattr(settings, 'BASE_DIR', 'Not set'),
        'debug': getattr(settings, 'DEBUG', False),
        'allowed_hosts': getattr(settings, 'ALLOWED_HOSTS', []),
        'secure_ssl_redirect': getattr(settings, 'SECURE_SSL_REDIRECT', False),
        'use_https': request.is_secure(),
        'host': request.get_host(),
        'protocol': 'https' if request.is_secure() else 'http',
    }

    possible_paths = [
        os.path.join(settings.STATIC_ROOT, 'firebase-messaging-sw.js'),
        os.path.join(settings.BASE_DIR, 'static', 'firebase-messaging-sw.js'),
        os.path.join(settings.BASE_DIR, 'staticfiles', 'firebase-messaging-sw.js'),
    ]

    file_status = {}
    for path in possible_paths:
        file_status[path] = {
            'exists': os.path.exists(path),
            'readable': os.path.isfile(path) and os.access(path, os.R_OK) if os.path.exists(path) else False,
            'size': os.path.getsize(path) if os.path.exists(path) else 0,
        }

    debug_info['files'] = file_status
    output = []
    output.append("=== FCM Debug Info ===\n")

    for key, value in debug_info.items():
        if key == 'files':
            output.append(f"{key}:")
            for file_path, status in value.items():
                output.append(f"  {file_path}:")
                for status_key, status_value in status.items():
                    output.append(f"    {status_key}: {status_value}")
        else:
            output.append(f"{key}: {value}")

    return HttpResponse('\n'.join(output), content_type='text/plain')


@require_http_methods(["GET"])
def test_https(request):
    """
    Тестирование HTTPS соединения
    """
    info = {
        'is_secure': request.is_secure(),
        'scheme': request.scheme,
        'host': request.get_host(),
        'full_url': request.build_absolute_uri(),
        'headers': dict(request.headers),
    }

    return HttpResponse(f"HTTPS Test: {info}", content_type='text/plain')

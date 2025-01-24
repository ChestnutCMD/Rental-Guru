from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from franchise.models import Franchise
from manager.filters import ManagerPermissionFilter
from manager.models import ManagerPermission, Manager
from manager.permissions import IsAdminOrSelf, IsAdmin
from manager.serializers import ManagerPermissionSerializer, ManagerUpdateSerializer, ManagerDetailSerializer, \
    ManagerListSerializer, ManagerCreateSerializer


@extend_schema(
        summary="Управление доступами для менеджеров",
        description="CRUD доступа для менеджеров"
    )
class ManagerPermissionViewSet(ModelViewSet):
    queryset = ManagerPermission.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ManagerPermissionFilter
    serializer_class = ManagerPermissionSerializer


@extend_schema(
        summary="Список моделей для настройки доступа",
        description="Список моделей для настройки доступа"
    )
class AvailableModelsView(APIView):
    """
    Эндпоинт для получения списка доступных моделей.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        content_types = ContentType.objects.all()

        models = [
            {
                "id": content_type.id,
                "app_label": content_type.app_label,
                "model": content_type.model,
                "name": content_type.name,
            }
            for content_type in content_types
        ]

        return Response(models)


@extend_schema(
        summary="Менеджеры, CRUD",
        description="CRUD для менеджеров"
    )
class ManagerViewSet(ModelViewSet):
    queryset = Manager.objects.select_related('user', 'manager_document').prefetch_related('permissions').all()
    permission_classes = [IsAuthenticated, IsAdminOrSelf]

    def get_serializer_class(self):
        if self.action == 'create':
            return ManagerCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ManagerUpdateSerializer
        if self.action == 'retrieve':
            return ManagerDetailSerializer
        return ManagerListSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """Удаление инфлюенсера и связанного пользователя."""
        instance = self.get_object()

        with transaction.atomic():
            user = instance.user
            user.delete()
            instance.delete()

        return Response(
            {"message": "Менеджер и связанный пользователь успешно удалены."},
            status=status.HTTP_204_NO_CONTENT,
        )

    def get_queryset(self):
        user = self.request.user
        franchise = Franchise.objects.filter(director=user).first()
        if franchise:
            return Manager.objects.filter(franchise=franchise)

        if user.role in ['admin', 'manager']:
            return Manager.objects.all()
        return Manager.objects.none()

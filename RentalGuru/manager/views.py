from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

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
    serializer_class = ManagerPermissionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        manager_id = self.request.query_params.get('manager_id')
        if manager_id:
            return self.queryset.filter(manager_id=manager_id)
        return self.queryset


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
            return [IsAuthenticated, IsAdmin]
        return super().get_permissions()

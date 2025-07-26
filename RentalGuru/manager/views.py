import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from franchise.models import Franchise
from manager.models import AccessType, Manager
from manager.permissions import IsAdminOrSelf, IsAdmin, StaffAccess, IsFranchiseDirector, IsDirector
from manager.serializers import AccessTypeSerializer, ManagerUpdateSerializer, ManagerDetailSerializer, \
    ManagerListSerializer, ManagerCreateSerializer


logger = logging.getLogger(__name__)

@extend_schema(
    summary="Типы доступов для менеджеров",
    description="Получение списка доступных типов доступов"
)
class AccessTypeViewSet(ReadOnlyModelViewSet):
    """ViewSet для получения списка типов доступов"""
    queryset = AccessType.objects.all()
    serializer_class = AccessTypeSerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    summary="Менеджеры, CRUD",
    description="CRUD для менеджеров"
)
class ManagerViewSet(ModelViewSet):
    """ViewSet для управления менеджерами"""
    queryset = Manager.objects.select_related('user', 'manager_document').prefetch_related('access_types', 'cities')
    permission_classes = [StaffAccess | IsDirector]

    def get_serializer_class(self):
        if self.action == 'create':
            return ManagerCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ManagerUpdateSerializer
        if self.action == 'retrieve':
            return ManagerDetailSerializer
        return ManagerListSerializer

    def get_permissions(self):
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        """Удаление менеджера и связанного пользователя"""
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

        if user.role == 'admin':
            return Manager.objects.all()

        if user.role == 'director':
            franchise = Franchise.objects.filter(director=user).first()
            if franchise:
                return Manager.objects.filter(cities=franchise.city)

        if user.role == 'manager' and hasattr(user, 'manager'):
            manager = user.manager
            if manager and manager.access_types.filter(name='staff').exists():
                return Manager.objects.all()

        return Manager.objects.none()
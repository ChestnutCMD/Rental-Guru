from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from franchise.models import Franchise
from manager.models import AccessType, Manager
from manager.permissions import IsAdminOrSelf, IsAdminOrDirector, IsAdmin, StaffAccess
from manager.serializers import AccessTypeSerializer, ManagerUpdateSerializer, ManagerDetailSerializer, \
    ManagerListSerializer, ManagerCreateSerializer


@extend_schema(
        summary="Типы доступов для менеджеров",
        description="Получение списка доступных типов доступов"
    )
class AccessTypeViewSet(ReadOnlyModelViewSet):
    """ViewSet для получения списка типов доступов"""
    queryset = AccessType.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AccessTypeSerializer



@extend_schema(
        summary="Менеджеры, CRUD",
        description="CRUD для менеджеров"
    )
class ManagerViewSet(ModelViewSet):
    queryset = Manager.objects.select_related('user', 'manager_document').prefetch_related('access_types').all()
    permission_classes = [StaffAccess, IsAdminOrSelf]

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
        """Удаление менеджера и связанного пользователя."""
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

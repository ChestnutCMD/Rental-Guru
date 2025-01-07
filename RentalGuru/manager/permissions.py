from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import BasePermission, SAFE_METHODS

from manager.models import ManagerPermission


class ManagerObjectPermission(BasePermission):
    """
    Проверяет права менеджера на доступ к объекту.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated or not hasattr(request.user, 'manager'):
            return False

        manager = request.user.manager
        content_type = ContentType.objects.get_for_model(obj)

        # Проверяем глобальные права
        if ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
            permission_type='read',
            is_global=True
        ).exists():
            return True

        # Проверяем объектные права
        return ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
            object_id=obj.id,
            permission_type='read'
        ).exists()


    """
    def get_permissions(self):
        if hasattr(self.request.user, 'manager') and self.request.user.manager:
            return [ManagerObjectPermission]
        return super().get_permissions()
    """


class IsAdminOrReadOnly(BasePermission):
    """
    Разрешает чтение всем, а изменение только администраторам.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role == 'manager' and obj.user == request.user:
            if 'permissions' in request.data:
                return False
            return True
        return False


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == 'admin':
            return True
        return False

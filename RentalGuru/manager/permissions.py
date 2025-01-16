from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import BasePermission, SAFE_METHODS

from manager.models import ManagerPermission


class ManagerObjectPermission(BasePermission):
    """
    Проверяет права менеджера на доступ к объекту.
    """
    def get_permission_type(self, request):
        """Определяет необходимый тип разрешения на основе метода запроса"""
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return 'read'
        elif request.method in ['PUT', 'PATCH']:
            return 'edit'
        elif request.method == 'DELETE':
            return 'delete'
        elif request.method == 'POST':
            return 'edit'  # или можно добавить специальный тип 'create'
        return 'read'

    def has_object_permission(self, request, view, obj):
        # Админы имеют полный доступ
        if request.user.is_authenticated and request.user.role == 'admin':
            return True

        if not request.user.is_authenticated or not hasattr(request.user, 'manager'):
            return False

        manager = request.user.manager
        content_type = ContentType.objects.get_for_model(obj)
        permission_type = self.get_permission_type(request)

        # Проверяем глобальные права
        if ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
            permission_type=permission_type,
            is_global=True
        ).exists():
            return True

        # Проверяем объектные права
        return ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
            object_id=obj.id,
            permission_type=permission_type
        ).exists()


class WebSocketPermissionChecker:
    """
    Класс для проверки прав доступа пользователя к объектам через WebSocket.
    """

    @staticmethod
    def has_permission(user, obj):
        """
        Проверяет, есть ли у пользователя права на доступ к объекту.
        """
        if user.role == 'admin':
            return True

        if not user.is_authenticated or not hasattr(user, 'manager'):
            return False

        content_type = ContentType.objects.get_for_model(obj)

        if ManagerPermission.objects.filter(
            manager=user.manager,
            content_type=content_type,
            permission_type='read',
            is_global=True
        ).exists():
            return True

        return ManagerPermission.objects.filter(
            manager=user.manager,
            content_type=content_type,
            object_id=obj.id,
            permission_type='read'
        ).exists()

    @staticmethod
    def check_chat_permission(user, chat):
        """
        Проверка прав доступа пользователя к чату.
        """
        return WebSocketPermissionChecker.has_permission(user, chat)

    """
    def get_permissions(self):
        if hasattr(self.request.user, 'manager') and self.request.user.manager:
            return [ManagerObjectPermission()]
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

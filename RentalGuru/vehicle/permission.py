from rest_framework import permissions

from manager.permissions import ManagerObjectPermission


class IsAdminOrReadOnly(ManagerObjectPermission):
    """
    Пользовательское разрешение, позволяющее создавать, редактировать и удалять объекты только администраторам.
    Доступ на чтение разрешен всем пользователям.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if super().has_object_permission(request, view, obj):
            return True


class IsAdminOrLessor(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее создавать объекты только администраторам и арендодателям.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role in ['admin', 'manager'] or hasattr(request.user, 'lessor'))


class IsAdminOrOwner(ManagerObjectPermission):
    """
    Пользовательское разрешение, позволяющее редактировать объект только администраторам или владельцам объекта.
    """
    def has_object_permission(self, request, view, obj):
        if super().has_object_permission(request, view, obj):
            return True
        return obj.owner == request.user

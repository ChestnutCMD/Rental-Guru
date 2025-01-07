from rest_framework import permissions


class IsAdminOrReadOnly(permissions.BasePermission):
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
        return request.user and request.user.role == 'admin'


class IsAdminOrLessor(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее создавать объекты только администраторам и арендодателям.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'admin' or hasattr(request.user, 'lessor'))


class IsAdminOrOwner(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее редактировать объект только администраторам или владельцам объекта.
    """
    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.owner == request.user

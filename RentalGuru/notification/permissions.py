from rest_framework.permissions import BasePermission


class IsAdminOrOwner(BasePermission):
    """
    Пользовательское разрешение, позволяющее редактировать объект только администраторам или владельцам объекта.
    """
    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.owner == request.user


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin' or request.user.role == 'manager'


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'manager'


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ('admin', 'manager'):
            return True
        return hasattr(request.user, 'renter') and obj.renter == request.user.renter


class IsAdminOrOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'admin':
            return True
        if hasattr(request.user, 'renter') and obj.renter == request.user.renter:
            return True
        return False


class HasRenter(BasePermission):
    """
    Проверяет, что у пользователя есть привязанный объект renter.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if not hasattr(request.user, 'renter'):
            raise PermissionDenied("Пользователь не авторизован либо не является арендатором")
        return True
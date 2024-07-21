from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'


class IsAdminOrLessor(permissions.BasePermission):
    """
    Custom permission to only allow admins and lessors to create objects.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'admin' or hasattr(request.user, 'lessor'))


class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to only allow admins or owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.owner == request.user

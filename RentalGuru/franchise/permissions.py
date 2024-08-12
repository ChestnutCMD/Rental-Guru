from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner or request.user.role == 'admin'

    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            return request.user and request.user.is_authenticated
        return True


class IsOwnerOrAdminForGet(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner or request.user.role == 'admin'
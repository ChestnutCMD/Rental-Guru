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
        if request.method not in ['GET']:
            return request.user == obj.owner or request.user.role == 'admin' or request.user.role == 'manager'

        if request.user.role == 'admin':
            return True

        if hasattr(obj, 'franchise'):
            if obj.franchise and request.user == obj.franchise.director:
                return True

        return request.user == obj.owner

    def has_permission(self, request, view):
        if request.user.role == 'admin':
            return True
        return super().has_permission(request, view)


class IsDirectorOrAdminForGet(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.director or request.user.role == 'admin'


class IsAdminOrManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin' or request.user.role == 'manager'


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

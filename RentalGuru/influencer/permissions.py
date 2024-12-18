from rest_framework import permissions


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'POST', 'LIST']:
            return request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'manager')
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdminOrInfluencer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user.role in ['admin', 'manager'] or obj.user == request.user


class IsAdminOrManagerForRequest(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager']

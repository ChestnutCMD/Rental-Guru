from rest_framework import permissions

class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        # Проверка прав для списка (GET) или создания (POST)
        if request.method == 'GET':
            return request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'manager')
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdminOrInfluencer(permissions.BasePermission):
    def has_permission(self, request, view):
        # Разрешение на просмотр или удаление объекта
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.user == request.user

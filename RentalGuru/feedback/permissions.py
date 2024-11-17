from rest_framework import permissions


class IsOwnerOrAdminOrManager(permissions.BasePermission):
    """
    Разрешение для изменения/удаления отзыва только владельцем отзыва или пользователями с ролью 'admin' или 'manager'.
    """
    def has_object_permission(self, request, view, obj):
        if request.user == obj.user:
            return True
        if request.user.role in ['admin', 'manager']:
            return True
        return False


class IsRenterOrAdminOrManager(permissions.BasePermission):
    """
    Разрешение для добавления/редактирования ответа только арендатором или пользователями с ролью 'admin' или 'manager'.
    """
    def has_object_permission(self, request, view, obj):
        if request.user == obj.renter:
            return True
        if request.user.role in ['admin', 'manager']:
            return True
        return False
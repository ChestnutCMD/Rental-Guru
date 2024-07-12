from rest_framework import permissions

from app.models import Renter
from .models import Trip, Chat, Message


class IsAdminOrOwner(permissions.BasePermission):
    """
    Разрешение позволяет доступ только пользователям с ролью 'admin' или владельцам ресурса.
    """

    def has_object_permission(self, request, view, obj):
        # Администраторы имеют полный доступ
        if request.user.role == 'admin':
            return True

        # Проверка принадлежности ресурса пользователю
        if isinstance(obj, Trip):
            return obj.renter == request.user
        elif isinstance(obj, Chat):
            return request.user in obj.participants.all()
        elif isinstance(obj, Message):
            return request.user in obj.chat.participants.all()

        return False

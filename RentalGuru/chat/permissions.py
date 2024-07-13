from rest_framework import permissions

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


class IsParticipantOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Администратор имеет доступ ко всем чатам
        if request.user.role == 'admin':
            return True
        # Участники чата имеют доступ только к своим чатам
        return request.user in obj.participants.all()


class IsChatCreatorOrAdmin(permissions.BasePermission):
    """
    Разрешение для разрешения доступа к действиям чата только создателю чата или администратору.
    """

    def has_object_permission(self, request, view, obj):
        # Разрешить GET запросы для всех пользователей
        if request.method in permissions.SAFE_METHODS:
            return True

        # Разрешить обновление только создателю чата или администратору
        return obj.creator == request.user or request.user.role == 'admin'

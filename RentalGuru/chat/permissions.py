from datetime import date

from rest_framework import permissions

from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic
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
        if request.user.role == 'admin':
            return True
        return request.user in obj.participants.all()


class IsChatCreatorOrAdmin(permissions.BasePermission):
    """
    Разрешение для разрешения доступа к действиям чата только создателю чата или администратору.
    """
    def has_permission(self, request, view):
        if request.method == 'POST':
            return True
        return True

    def has_object_permission(self, request, view, obj):
        return obj.creator == request.user or request.user.role == 'admin'


class IsOrganizerAndEndDateToday(permissions.BasePermission):
    def has_permission(self, request, view):
        vehicle_id = request.data.get('Vehicle_id')
        vehicle_type = request.data.get('Vehicle_type')

        if not vehicle_id or not vehicle_type:
            return False

        model = {
            'Auto': Auto,
            'Bike': Bike,
            'Ship': Ship,
            'Helicopter': Helicopter,
            'SpecialTechnic': SpecialTechnic
        }.get(vehicle_type)

        if not model:
            return False

        try:
            trip = Trip.objects.get(vehicle__id=vehicle_id, vehicle__polymorphic_ctype__model=model.__name__.lower())
        except Trip.DoesNotExist:
            return False

        if trip.organizer == request.user and trip.end_date == date.today():
            return True

        return False

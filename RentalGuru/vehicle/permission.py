from django.utils import timezone
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from chat.models import Trip
from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее создавать, редактировать и удалять объекты только администраторам.
    Доступ на чтение разрешен всем пользователям.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.role == 'admin'


class IsAdminOrLessor(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее создавать объекты только администраторам и арендодателям.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.role == 'admin' or hasattr(request.user, 'lessor'))


class IsAdminOrOwner(permissions.BasePermission):
    """
    Пользовательское разрешение, позволяющее редактировать объект только администраторам или владельцам объекта.
    """
    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin' or obj.owner == request.user


class IsTripOrganizerAndValid(permissions.BasePermission):
    """
    Разрешение, которое проверяет, что пользователь является организатором поездки,
    поездка связана с текущим транспортным средством, и дата завершения поездки не превышает текущую дату.
    """

    def has_permission(self, request, view):
        # Необходимо, чтобы все проверки были выполнены в методе has_object_permission
        return True

    def has_object_permission(self, request, view, obj):
        # Получаем данные из запроса
        vehicle_type = request.data.get('Vehicle_type')
        vehicle_id = request.data.get('Vehicle_id')

        if not vehicle_type or not vehicle_id:
            raise PermissionDenied("Требуется указать тип транспортного средства и идентификационный номер.")

        # Определяем модель транспортного средства
        model = {
            'Auto': Auto,
            'Bike': Bike,
            'Ship': Ship,
            'Helicopter': Helicopter,
            'SpecialTechnic': SpecialTechnic
        }.get(vehicle_type)

        if not model:
            raise PermissionDenied("Неверный тип транспорта")

        try:
            vehicle = model.objects.get(id=vehicle_id)
        except model.DoesNotExist:
            raise PermissionDenied("Транспорт не найден")

        # Проверяем, существует ли поездка с указанным транспортным средством
        try:
            trip = Trip.objects.get(vehicle=vehicle, organizer=request.user)
        except Trip.DoesNotExist:
            raise PermissionDenied("Не найдено поездки для данного транспорта и пользователя.")

        # Проверяем, что дата завершения поездки не превышает текущую дату
        if trip.end_date > timezone.now().date():
            raise PermissionDenied("Поездка еще не завершилась")

        return True

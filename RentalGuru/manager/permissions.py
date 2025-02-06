import logging

from django.contrib.contenttypes.models import ContentType
from rest_framework.permissions import BasePermission, SAFE_METHODS

from franchise.models import Franchise
from manager.models import ManagerPermission


class CheckManagerPermission(BasePermission):
    """
    Проверяет права менеджера на доступ к объекту.
    """
    def get_permission_type(self, request):
        """Определяет необходимый тип разрешения на основе метода запроса"""
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return 'read'
        elif request.method in ['PUT', 'PATCH']:
            return 'edit'
        elif request.method == 'DELETE':
            return 'delete'
        elif request.method == 'POST':
            return 'edit'
        return 'read'

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and request.user.role == 'admin':
            return True

        if not request.user.is_authenticated or not hasattr(request.user, 'manager'):
            return False

        manager = request.user.manager
        content_type = ContentType.objects.get_for_model(obj)
        permission_type = self.get_permission_type(request)

        if ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
            permission_type=permission_type,
            is_global=True
        ).exists():
            return True

        return ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
            object_id=obj.id,
            permission_type=permission_type
        ).exists()


logger = logging.getLogger('payment')


class IsFranchiseDirector(BasePermission):
    """
    Разрешает доступ директору франшизы ко всем объектам, относящимся к его франшизе.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Получаем франшизу пользователя
        franchise = Franchise.objects.filter(director=request.user).first()
        if not franchise:
            return False

        # Проверяем, принадлежит ли объект этой франшизе
        return self._is_object_in_franchise(franchise, obj)

    def _is_object_in_franchise(self, franchise, obj):
        """
        Проверяет, принадлежит ли объект указанной франшизе.
        """
        model_checks = {
            'auto': lambda obj: obj.owner.lessor.franchise,
            'bike': lambda obj: obj.owner.lessor.franchise,
            'ship': lambda obj: obj.owner.lessor.franchise,
            'helicopter': lambda obj: obj.owner.lessor.franchise,
            'specialtechnic': lambda obj: obj.owner.lessor.franchise,
            'vehicle': lambda obj: obj.owner.lessor.franchise,
            'lessor': lambda obj: obj.franchise,
            'user': lambda obj: obj.lessor.franchise,
            'chat': lambda obj: obj.request_rent.vehicle.owner.lessor.franchise,
            'feedback': lambda obj: obj.vehicle.owner.lessor.franchise,
            'requestrent': lambda obj: obj.vehicle.owner.lessor.franchise,
            'trip': lambda obj: obj.vehicle.owner.lessor.franchise,
            'franchise': lambda obj: obj,
            'complaint': lambda obj: obj.vehicle.owner.lessor.franchise,
            'complaintforfeedback': lambda obj: obj.feedback.vehicle.owner.lessor.franchise,
        }

        model_name = obj._meta.model_name.lower()
        check_function = model_checks.get(model_name)

        return check_function(obj) == franchise if check_function else False


class UniversalPermission(BasePermission):
    """
    Универсальный пермишн для проверки прав доступа менеджеров и директоров франшизы.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Получаем франшизу пользователя, если он является директором
        franchise = Franchise.objects.filter(director=request.user).first()

        if not franchise:
            logger.warning(f"User {request.user} is not a director of any franchise")

        # Если пользователь — директор франшизы, проверяем, принадлежит ли объект его франшизе
        if franchise and self._is_object_in_franchise(franchise, obj):
            logger.info(f"User {request.user} is a director and has access to {obj}")
            return True

        # Проверка, является ли пользователь менеджером франшизы
        if request.user.role != 'manager' or not hasattr(request.user, 'manager'):
            return False

        manager = request.user.manager
        if not manager or not manager.franchise:
            return False

        content_type = ContentType.objects.get_for_model(obj)

        logger.info(f"Checking permissions for manager {manager} on {obj}")

        # Проверка, есть ли у менеджера разрешение на данный тип объекта
        if not self._has_permission(manager, content_type):
            logger.warning(f"Manager {manager} does not have permission for {content_type}")
            return False

        # Проверка принадлежности объекта франшизе менеджера
        return self._is_object_in_franchise(manager.franchise, obj)

    def _has_permission(self, manager, content_type):
        """
        Проверяет, есть ли у менеджера права на указанный content_type.
        """
        return ManagerPermission.objects.filter(
            manager=manager,
            content_type=content_type,
        ).exists()

    def _is_object_in_franchise(self, franchise, obj):
        """
        Проверяет, принадлежит ли объект указанной франшизе.
        """
        if not obj:
            return False

        model_name = ContentType.objects.get_for_model(obj).model.lower()

        model_checks = {
            'auto': lambda obj: getattr(obj.owner, 'lessor', None) and obj.owner.lessor.franchise,
            'bike': lambda obj: getattr(obj.owner, 'lessor', None) and obj.owner.lessor.franchise,
            'ship': lambda obj: getattr(obj.owner, 'lessor', None) and obj.owner.lessor.franchise,
            'helicopter': lambda obj: getattr(obj.owner, 'lessor', None) and obj.owner.lessor.franchise,
            'specialtechnic': lambda obj: getattr(obj.owner, 'lessor', None) and obj.owner.lessor.franchise,
            'vehicle': lambda obj: getattr(obj.owner, 'lessor', None) and obj.owner.lessor.franchise,
            'lessor': lambda obj: obj.franchise,
            'user': lambda obj: getattr(obj, 'lessor', None) and obj.lessor.franchise,
            'chat': lambda obj: getattr(obj.request_rent.vehicle.owner, 'lessor',
                                        None) and obj.request_rent.vehicle.owner.lessor.franchise,
            'feedback': lambda obj: getattr(obj.vehicle.owner, 'lessor', None) and obj.vehicle.owner.lessor.franchise,
            'requestrent': lambda obj: getattr(obj.vehicle.owner, 'lessor',
                                               None) and obj.vehicle.owner.lessor.franchise,
            'trip': lambda obj: getattr(obj.vehicle.owner, 'lessor', None) and obj.vehicle.owner.lessor.franchise,
            'franchise': lambda obj: obj,
            'complaint': lambda obj: getattr(obj.vehicle.owner, 'lessor', None) and obj.vehicle.owner.lessor.franchise,
            'complaintforfeedback': lambda obj: getattr(obj.feedback.vehicle.owner, 'lessor',
                                                        None) and obj.feedback.vehicle.owner.lessor.franchise,
        }

        check_function = model_checks.get(model_name)

        if not check_function:
            logger.warning(f"Model {model_name} is not found in permissions map")
            return False

        result = check_function(obj) == franchise
        logger.info(f"Checking franchise ownership: {result} for model {model_name} and user {franchise.director}")

        return result


class ManagerObjectPermission(BasePermission):
    """
    Комбинированный пермишн, использующий UniversalPermission при наличии франшизы
    и ManagerObjectPermission при её отсутствии.
    """

    def has_object_permission(self, request, view, obj):
        manager = getattr(request.user, 'manager', None)
        if manager and manager.franchise:
            return UniversalPermission().has_object_permission(request, view, obj)
        else:
            return CheckManagerPermission().has_object_permission(request, view, obj)


class WebSocketPermissionChecker:
    """
    Класс для проверки прав доступа пользователя к объектам через WebSocket.
    """

    @staticmethod
    def has_permission(user, obj):
        """
        Проверяет, есть ли у пользователя права на доступ к объекту.
        """
        if user.role == 'admin':
            return True

        if not user.is_authenticated or not hasattr(user, 'manager'):
            return False

        content_type = ContentType.objects.get_for_model(obj)

        if ManagerPermission.objects.filter(
            manager=user.manager,
            content_type=content_type,
            permission_type='read',
            is_global=True
        ).exists():
            return True

        return ManagerPermission.objects.filter(
            manager=user.manager,
            content_type=content_type,
            object_id=obj.id,
            permission_type='read'
        ).exists()

    @staticmethod
    def check_chat_permission(user, chat):
        """
        Проверка прав доступа пользователя к чату.
        """
        return WebSocketPermissionChecker.has_permission(user, chat)

    """
    def get_permissions(self):
        if hasattr(self.request.user, 'manager') and self.request.user.manager:
            return [ManagerObjectPermission()]
        return super().get_permissions()
    """


class IsAdminOrReadOnly(BasePermission):
    """
    Разрешает чтение всем, а изменение только администраторам.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'admin'


class IsAdminOrSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if request.user.role == 'manager' and obj.user == request.user:
            if 'permissions' in request.data:
                return False
            return True
        return False


class IsAdminOrDirector(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == 'admin':
            return True
        elif request.user.franchise:
            return True
        return False


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        if request.user.role == 'admin':
            return True
        return False

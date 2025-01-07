import django_filters
from django_filters import rest_framework as filters
from .models import ManagerPermission


class ManagerPermissionFilter(filters.FilterSet):
    """
    Фильтры для модели ManagerPermission.
    """
    manager_id = django_filters.NumberFilter(field_name="manager__id", lookup_expr="exact")

    class Meta:
        model = ManagerPermission
        fields = ['manager_id']

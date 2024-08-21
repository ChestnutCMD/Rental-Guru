from rest_framework import permissions

from franchise.models import Franchise


class IsAdminManagerOrFranchiseOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.user.role in ['admin', 'manager']:
            return True

        franchise_id = view.kwargs.get('franchise_id')
        return request.user == Franchise.objects.get(id=franchise_id).director

from rest_framework import permissions

from franchise.models import Franchise

class IsAdminManagerOrFranchiseOwner(permissions.BasePermission):
    def has_permission(self, request, view):

        if request.user.role in ['admin', 'manager']:
            return True

        franchise_id = view.kwargs.get('franchise_id')
        if not franchise_id:
            return False

        try:
            franchise = Franchise.objects.get(id=franchise_id)
        except Franchise.DoesNotExist:
            return False

        return request.user == franchise.director

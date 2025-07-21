from rest_framework import permissions

from franchise.models import Franchise

class IsAdminManagerOrFranchiseOwner(permissions.BasePermission):
    def has_permission(self, request, view):

        if request.user.role in ['admin', 'manager']:
            return True

        return Franchise.objects.filter(director=request.user).exists()

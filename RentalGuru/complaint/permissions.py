from rest_framework import permissions


class IsMemberOrManagerAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action == 'create':
            return request.user.role == 'member'
        return request.user.role in ['manager', 'administrator']

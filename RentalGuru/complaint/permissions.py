from rest_framework import permissions


class IsMemberOrManagerAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        if view.action in ['create', 'destroy']:
            return request.user.role == 'member'
        elif view.action in ['list', 'retrieve']:
            return True
        return request.user.role in ['manager', 'administrator']

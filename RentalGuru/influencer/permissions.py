from rest_framework import permissions
from rest_framework.permissions import BasePermission

from influencer.models import Influencer
from manager.permissions import ManagerObjectPermission


class IsAdminOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'POST', 'LIST']:
            return request.user.is_authenticated and (request.user.role == 'admin' or request.user.role == 'manager')
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsAdminOrInfluencer(ManagerObjectPermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if super().has_object_permission(request, view, obj):
            return True
        return obj.user == request.user


class IsAdminOrOwner(BasePermission):
    def has_permission(self, request, view):
        if request.user.role in ['admin', 'manager']:
            return True
        influencer_id = view.kwargs.get('influencer_id')
        influencer = Influencer.objects.filter(id=influencer_id).first()
        return influencer and influencer.user == request.user

    def has_object_permission(self, request, view, obj):
        return obj.influencer.user == request.user


class IsAdminOrManagerForRequest(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'manager']

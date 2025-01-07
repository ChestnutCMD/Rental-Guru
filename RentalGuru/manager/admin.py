from django.contrib import admin
from .models import Manager, ManagerDocuments, ManagerPermission


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ['user']
    search_fields = ['user__email']


@admin.register(ManagerDocuments)
class ManagerDocumentsAdmin(admin.ModelAdmin):
    list_display = ['manager', 'number']


@admin.register(ManagerPermission)
class ManagerPermissionAdmin(admin.ModelAdmin):
    list_display = ['manager', 'content_type', 'object_id', 'permission_type', 'is_global']
    list_filter = ['content_type', 'permission_type', 'is_global']
    search_fields = ['manager__user__email']

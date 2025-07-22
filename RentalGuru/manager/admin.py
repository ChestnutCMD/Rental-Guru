from django.contrib import admin
from .models import Manager, ManagerDocuments, AccessType


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ['user', 'franchise']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    list_filter = ['franchise', 'access_types']
    filter_horizontal = ['access_types']


@admin.register(ManagerDocuments)
class ManagerDocumentsAdmin(admin.ModelAdmin):
    list_display = ['manager', 'number']


@admin.register(AccessType)
class AccessTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_display_name']
    search_fields = ['name']
    
    def get_display_name(self, obj):
        return str(obj)
    get_display_name.short_description = 'Отображаемое имя'

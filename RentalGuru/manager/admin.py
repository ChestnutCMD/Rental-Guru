from django.contrib import admin
from .models import Manager, ManagerDocuments, AccessType


class AccessTypeInline(admin.TabularInline):
    model = Manager.access_types.through
    extra = 1


@admin.register(Manager)
class ManagerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'city')
    inlines = [AccessTypeInline]
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'user__email')
    list_filter = ('city', 'access_types')


@admin.register(ManagerDocuments)
class ManagerDocumentsAdmin(admin.ModelAdmin):
    list_display = ['manager', 'number']


@admin.register(AccessType)
class AccessTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'permission')
    list_filter = ('name', 'permission')
    search_fields = ('name',)
    ordering = ('name', 'permission')

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from chat.models import Trip
from vehicle.models import Vehicle


class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'organizer', 'get_owner', 'start_date', 'end_date', 'get_object', 'total_cost', 'status')
    list_filter = ('status', 'start_date', 'end_date', 'content_type')
    search_fields = ('organizer__name', 'status', 'object_id')
    date_hierarchy = 'start_date'
    list_per_page = 20

    def get_type(self, obj):
        return obj.content_type.model
    get_type.short_description = _('Тип транспорта')

    def get_object(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle) if vehicle else None
    get_object.short_description = _('Транспорт')

    def get_owner(self, obj):
        vehicle = Vehicle.objects.filter(id=obj.object_id).first()
        return str(vehicle.owner) if vehicle and vehicle.owner else None
    get_owner.short_description = _('Арендодатель')


admin.site.register(Trip, TripAdmin)

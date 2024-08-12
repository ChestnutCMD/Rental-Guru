from django.contrib import admin
from django.db.models import Q

from vehicle.models import Vehicle
from .models import Franchise, VehiclePark, RequestFranchise, Category


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


class VehicleInline(admin.TabularInline):
    model = Vehicle
    extra = 1
    readonly_fields = ('brand', 'model', 'year', 'location')

# Inline class for VehiclePark
class VehicleParkInline(admin.TabularInline):
    model = VehiclePark
    extra = 1
    readonly_fields = ('name',)

# Admin class for Franchise
class FranchiseAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'unn', 'date_register', 'telephone', 'email', 'country', 'city',
        'director', 'commission', 'total_vehicles', 'get_vehicles'
    )
    list_filter = ('country', 'city', 'director')
    search_fields = ('name', 'unn', 'email', 'telephone', 'country', 'city', 'director__email')
    readonly_fields = ('total_vehicles', 'date_register')

    inlines = [VehicleParkInline, VehicleInline]

    def save_model(self, request, obj, form, change):
        if change:
            obj.update_total_vehicles()
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related('vehicle_parks__vehicles')

    def get_vehicles(self, obj):
        vehicles = Vehicle.objects.filter(
            franchise=obj
        )
        return ", ".join([f'{v.brand.name} {v.model.name} ({v.year})' for v in vehicles])
    get_vehicles.short_description = 'Транспортные средства'

    def get_fieldsets(self, request, obj=None):
        return [
            ('Основная информация', {
                'fields': (
                    'name', 'unn', 'telephone', 'email', 'country', 'city',
                    'director', 'commission', 'total_vehicles'
                )
            }),
        ]


class VehicleParkAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'franchise')
    list_filter = ('owner', 'franchise')
    search_fields = ('name', 'owner__email', 'franchise__name')


class RequestFranchiseAdmin(admin.ModelAdmin):
    list_display = ('name', 'telephone', 'email', 'city')
    search_fields = ('name', 'telephone', 'email', 'city')


admin.site.register(Category, CategoryAdmin)
admin.site.register(Franchise, FranchiseAdmin)
admin.site.register(VehiclePark, VehicleParkAdmin)
admin.site.register(RequestFranchise, RequestFranchiseAdmin)

from django.contrib import admin
from .models import *

admin.site.site_header = "Rental Guru"
admin.site.site_title = "Rental Guru Admin"
admin.site.index_title = "CRM"
admin.site.css = {
            'all': ('css/custom_admin.css',)
        }


@admin.register(VehicleFeaturesFunctions)
class VehicleFeaturesFunctionsAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(AutoFeaturesAdditionally)
class AutoFeaturesAdditionallyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(BikeFeaturesAdditionally)
class BikeFeaturesAdditionallyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(ShipFeaturesAdditionally)
class ShipFeaturesAdditionallyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(FeaturesForChildren)
class FeaturesForChildrenAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(FeaturesEquipment)
class FeaturesEquipmentAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(VehicleBrand)
class VehicleBrandAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(VehicleModel)
class VehicleModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand')
    search_fields = ('name', 'brand__name')
    ordering = ('brand', 'name')


class AvailabilityInline(admin.TabularInline):
    model = Availability
    extra = 1


class VehicleDocumentInline(admin.TabularInline):
    model = VehicleDocument
    extra = 1


class VehiclePhotoInline(admin.TabularInline):
    model = VehiclePhoto
    extra = 1


class RentPriceInline(admin.TabularInline):
    model = RentPrice
    extra = 1
    readonly_fields = ('total',)


class BaseVehicleAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'year', 'owner', 'get_vehicle_type', 'get_average_rating')
    search_fields = ('brand__name', 'model__name', 'year', 'owner__email')
    list_filter = ('brand', 'model', 'year', 'owner')
    ordering = ('-year',)
    list_per_page = 20
    readonly_fields = ('ratings', 'get_average_rating')

    inlines = [AvailabilityInline, VehicleDocumentInline, RentPriceInline, VehiclePhotoInline]

    def get_vehicle_type(self, obj):
        return obj.__class__.__name__
    get_vehicle_type.short_description = 'Vehicle Type'

    def get_average_rating(self, obj):
        average_ratings = obj.get_average_rating()
        return ', '.join(f"{category}: {rating:.1f}" for category, rating in average_ratings.items())

    get_average_rating.short_description = 'Average Rating'

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            # Include the average rating in the fieldsets if the object exists
            fieldsets = list(fieldsets)  # Convert to list to modify
            fieldsets.append(('Рейтинг', {'fields': ('get_average_rating',)}))
        return fieldsets

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        availabilities = list(form.instance.availabilities.values('start_date', 'end_date'))
        if availabilities:
            merged_availabilities = merge_periods(availabilities)

            # Удаление всех текущих записей доступности
            form.instance.availabilities.all().delete()

            # Сохранение объединенных периодов доступности
            for availability in merged_availabilities:
                Availability.objects.create(vehicle=form.instance, **availability)


class AutoAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', )
        }),
        ('Характеристики', {
            'fields': ('brand', 'model', 'body_type', 'seats', 'transmission', 'fuel_type',
                       'year', 'description', 'long_distance', 'delivery', 'ensurance', 'vehicle_class',
                       'acceptable_mileage')
        }),
        ('Особенности', {
            'fields': ('features_for_children', 'features_functions', 'features_additionally')
        }),
        ('Условия аренды', {
            'fields': ('drivers_age', 'drivers_experience', 'drivers_rating', 'drivers_only_verified')
        }),
        ('Цены и скидки', {
            'fields': ('price_delivery', 'price_deposit', 'min_rent_day', 'max_rent_day',)
        }),
        ('Способ оплаты', {
            'fields': ('payment_method',)
        }),
        ('Местоположение', {
            'fields': ('location', )
        }),
        ('Рейтинг', {
            'fields': ('get_average_rating',),
            'classes': ('collapse',)
        })
    )


class BikeAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', )
        }),
        ('Характеристики', {
            'fields': ('brand', 'model', 'seats', 'engine_capacity', 'transmission', 'year', 'description',
                       'long_distance', 'delivery', 'ensurance', 'vehicle_class', 'acceptable_mileage')
        }),
        ('Особенности', {
            'fields': ('features_functions', 'features_additionally')
        }),
        ('Условия аренды', {
            'fields': ('drivers_age', 'drivers_experience', 'drivers_rating', 'drivers_only_verified')
        }),
        ('Цены и скидки', {
            'fields': ('price_delivery', 'price_deposit', 'min_rent_day', 'max_rent_day',)
        }),
        ('Способ оплаты', {
            'fields': ('payment_method',)
        }),
        ('Местоположение', {
            'fields': ('location',)
        }),
        ('Рейтинг', {
            'fields': ('get_average_rating',),
            'classes': ('collapse',)
        })
    )


class ShipAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', )
        }),
        ('Характеристики', {
            'fields': ('type_ship', 'brand', 'model', 'year', 'grot', 'length', 'width', 'precipitation', 'seats',
                       'sleeping_place', 'one_sleeping_place', 'two_sleeping_place', 'toilet', 'engine_capacity',
                       'water_tank', 'fuel_tank', 'description', 'long_distance', 'delivery', 'ensurance',
                       'vehicle_class', 'acceptable_mileage')
        }),
        ('Особенности', {
            'fields': ('features_functions', 'features_additionally', 'features_equipment')
        }),
        ('Условия аренды', {
            'fields': ('drivers_rating', 'drivers_only_verified')
        }),
        ('Цены и скидки', {
            'fields': ('price_delivery', 'price_deposit', 'min_rent_day', 'max_rent_day',)
        }),
        ('Способ оплаты', {
            'fields': ('payment_method',)
        }),
        ('Местоположение', {
            'fields': ('location',)
        }),
        ('Рейтинг', {
            'fields': ('get_average_rating',),
            'classes': ('collapse',)
        })
    )


class HelicopterAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', )
        }),
        ('Характеристики', {
            'fields': ('brand', 'model', 'year', 'max_speed', 'cruising_speed', 'flight_range',
                       'flight_duration', 'power_cruising', 'take_off_power', 'full_take_weight', 'payload',
                       'engine_capacity', 'fuel_tank', 'description', 'long_distance', 'delivery', 'ensurance',
                       'vehicle_class', 'acceptable_mileage')
        }),
        ('Условия аренды', {
            'fields': ('drivers_rating', 'drivers_only_verified')
        }),
        ('Цены и скидки', {
            'fields': ('price_delivery', 'price_deposit', 'min_rent_day', 'max_rent_day',)
        }),
        ('Способ оплаты', {
            'fields': ('payment_method',)
        }),
        ('Местоположение', {
            'fields': ('location',)
        }),
        ('Рейтинг', {
            'fields': ('get_average_rating',),
            'classes': ('collapse',)
        })
    )


class SpecialTechnicAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', )
        }),
        ('Характеристики', {
            'fields': ('type_technic', 'brand', 'model', 'year', 'engine_power', 'length', 'width', 'high',
                       'operating_weight', 'description', 'long_distance', 'delivery', 'ensurance')
        }),
        ('Условия аренды', {
            'fields': ('drivers_rating', 'drivers_only_verified')
        }),
        ('Цены и скидки', {
            'fields': ('price_delivery', 'price_deposit', 'min_rent_day', 'max_rent_day',)
        }),
        ('Способ оплаты', {
            'fields': ('payment_method',)
        }),
        ('Местоположение', {
            'fields': ('location',)
        }),
        ('Рейтинг', {
            'fields': ('get_average_rating',),
            'classes': ('collapse',)
        })
    )


admin.site.register(Auto, AutoAdmin)
admin.site.register(Bike, BikeAdmin)
admin.site.register(Ship, ShipAdmin)
admin.site.register(Helicopter, HelicopterAdmin)
admin.site.register(SpecialTechnic, SpecialTechnicAdmin)

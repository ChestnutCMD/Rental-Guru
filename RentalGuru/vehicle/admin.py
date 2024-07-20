from django.contrib import admin
from .models import *


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


class RentPriceInline(admin.TabularInline):
    model = RentPrice
    extra = 1
    readonly_fields = ('total',)


class BaseVehicleAdmin(admin.ModelAdmin):
    list_display = ('brand', 'model', 'year', 'owner', 'get_vehicle_type')
    search_fields = ('brand__name', 'model__name', 'year', 'owner__email')
    list_filter = ('brand', 'model', 'year', 'owner')
    ordering = ('-year',)
    list_per_page = 20

    inlines = [AvailabilityInline, VehicleDocumentInline, RentPriceInline]

    def get_vehicle_type(self, obj):
        return obj.__class__.__name__
    get_vehicle_type.short_description = 'Vehicle Type'


class AutoAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', 'ratings')
        }),
        ('Характеристики', {
            'fields': ('brand', 'model', 'body_type', 'seats', 'transmission', 'fuel_type',
                       'year', 'description', 'long_distance', 'delivery', 'ensurance', 'vehicle_class', 'acceptable_mileage')
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
        ('Фото', {
            'fields': ('photo', )
        }),
    )


class BikeAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', 'ratings')
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
        ('Фото', {
            'fields': ('photo',)
        }),
    )


class ShipAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', 'ratings')
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
        ('Фото', {
            'fields': ('photo',)
        }),
    )


class HelicopterAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', 'ratings')
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
        ('Фото', {
            'fields': ('photo',)
        }),
    )


class SpecialTechnicAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', 'ratings')
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
        ('Фото', {
            'fields': ('photo',)
        })
    )


admin.site.register(Auto, AutoAdmin)
admin.site.register(Bike, BikeAdmin)
admin.site.register(Ship, ShipAdmin)
admin.site.register(Helicopter, HelicopterAdmin)
admin.site.register(SpecialTechnic, SpecialTechnicAdmin)

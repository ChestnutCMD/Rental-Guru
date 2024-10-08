from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline
from tornado.escape import linkify

from chat.models import Feedback
from .models import *

admin.site.site_header = "Rental Guru"
admin.site.site_title = "Rental Guru Admin"
admin.site.index_title = "CRM"


class BaseFeatures(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    ordering = ('name',)


class BaseType(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title',)
    ordering = ('title',)

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = slugify(obj.title)
        super().save_model(request, obj, form, change)


@admin.register(VehicleFeaturesFunctions)
class VehicleFeaturesFunctionsAdmin(BaseFeatures):
    pass


@admin.register(AutoFeaturesAdditionally)
class AutoFeaturesAdditionallyAdmin(BaseFeatures):
    pass


@admin.register(BikeFeaturesAdditionally)
class BikeFeaturesAdditionallyAdmin(BaseFeatures):
    pass


@admin.register(ShipFeaturesAdditionally)
class ShipFeaturesAdditionallyAdmin(BaseFeatures):
    pass


@admin.register(FeaturesForChildren)
class FeaturesForChildrenAdmin(BaseFeatures):
    pass


@admin.register(FeaturesEquipment)
class FeaturesEquipmentAdmin(BaseFeatures):
    pass


@admin.register(PaymentMethod)
class PaymentMethodAdmin(BaseFeatures):
    pass


@admin.register(VehicleBrand)
class VehicleBrandAdmin(BaseFeatures):
    pass


@admin.register(VehicleModel)
class VehicleModelAdmin(BaseFeatures):
    pass


@admin.register(VehicleClass)
class VehicleClassAdmin(BaseType):
    pass


@admin.register(AutoFuelType)
class AutoFuelTypeAdmin(BaseType):
    pass


@admin.register(AutoTransmission)
class AutoTransmissionAdmin(BaseType):
    pass


@admin.register(AutoBodyType)
class AutoBodyTypeAdmin(BaseType):
    pass


@admin.register(BikeTransmission)
class BikeTransmission(BaseType):
    pass


class FeedbackInline(GenericStackedInline):
    model = Feedback
    extra = 1


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
    list_display = (linkify('brand'), linkify('model'), 'year', linkify('owner'), 'get_vehicle_type', 'get_average_rating')
    search_fields = ('brand__name', 'model__name', 'year', 'owner__email')
    list_filter = ('brand', 'model', 'year', 'owner')
    ordering = ('-year',)
    list_per_page = 20
    readonly_fields = ('get_average_rating',)

    inlines = [AvailabilityInline, VehicleDocumentInline, RentPriceInline, VehiclePhotoInline, FeedbackInline]

    def get_vehicle_type(self, obj):
        return obj.__class__.__name__

    get_vehicle_type.short_description = 'Тип транспорта'

    def get_average_rating(self, obj):
        average_ratings = obj.get_average_rating()
        return ', '.join(f"{category}: {rating:.1f}" for category, rating in average_ratings.items())

    get_average_rating.short_description = 'Рейтинг'

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj:
            fieldsets = list(fieldsets)
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

    def get_inline_instances(self, request, obj=None):
        inline_instances = super().get_inline_instances(request, obj)
        if not obj:

            inline_instances = [inline for inline in inline_instances if not isinstance(inline, FeedbackInline)]
        return inline_instances


class AutoAdmin(BaseVehicleAdmin):
    fieldsets = (
        (None, {
            'fields': ('owner', 'verified')
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
        })
    )


admin.site.register(Auto, AutoAdmin)
admin.site.register(Bike, BikeAdmin)
admin.site.register(Ship, ShipAdmin)
admin.site.register(Helicopter, HelicopterAdmin)
admin.site.register(SpecialTechnic, SpecialTechnicAdmin)

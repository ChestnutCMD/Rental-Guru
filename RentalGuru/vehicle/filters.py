from itertools import chain

from asgiref.sync import sync_to_async
from django.db.models import Q
from django_filters import rest_framework as filters
from haversine import haversine, Unit

from vehicle.models import AutoFeaturesAdditionally, Auto, Bike, Ship, Helicopter, SpecialTechnic, VehicleModel, \
    BikeFeaturesAdditionally, ShipFeaturesAdditionally, FeaturesForChildren, VehicleFeaturesFunctions, FeaturesEquipment


class BaseFilter(filters.FilterSet):
    super_host = filters.BooleanFilter(field_name='owner__lessor__super_host', label='Суперхост')
    day_price = filters.RangeFilter(field_name='rent_prices__price', label='Дневная цена')
    verified_only = filters.BooleanFilter(field_name='drivers_only_verified',
                                          label='Сдается только верифицированным пользователям')
    brand = filters.CharFilter(method='filter_by_brand', label='Марка')
    year = filters.RangeFilter(field_name='year', label='Год выпуска')
    rental_date = filters.DateFromToRangeFilter(method='filter_by_rental_date', label='Выбор даты аренды')
    city = filters.CharFilter(field_name='city__title', label='Город')

    lat = filters.NumberFilter(method='filter_by_lat_lon', label='Широта')
    lon = filters.NumberFilter(method='filter_by_lat_lon', label='Долгота')
    radius = filters.NumberFilter(method='filter_by_lat_lon', label='Радиус в км', required=False)

    class Meta:
        abstract = True

    def filter_by_rental_date(self, queryset, name, value):
        """
        Фильтрация по диапазону дат аренды, чтобы начальная дата фильтра была позже или совпадала с
        availabilities__start_date, а конечная дата была раньше или совпадала с availabilities__end_date.
        """
        if value.start and value.stop:
            queryset = queryset.filter(
                Q(availabilities__start_date__lte=value.start) & Q(availabilities__end_date__gte=value.stop)
            )
        elif value.start:
            queryset = queryset.filter(availabilities__start_date__lte=value.start)
        elif value.stop:
            queryset = queryset.filter(availabilities__end_date__gte=value.stop)
        return queryset

    def filter_by_brand(self, queryset, name, value):
        brand_names = value.split(",")
        return queryset.filter(brand__name__in=brand_names)

    def filter_by_lat_lon(self, queryset, name, value):
        lat = self.data.get('lat')
        lon = self.data.get('lon')
        radius = self.data.get('radius', 5)  # Радиус по умолчанию 5 км, если не передан

        if lat and lon:
            lat = float(lat)
            lon = float(lon)
            radius = float(radius)
            user_location = (lat, lon)

            filtered_queryset = []

            for vehicle in queryset:
                if vehicle.latitude and vehicle.longitude:
                    vehicle_location = (vehicle.latitude, vehicle.longitude)
                    distance = haversine(user_location, vehicle_location, unit=Unit.KILOMETERS)

                    if distance <= radius:
                        filtered_queryset.append(vehicle)

            return queryset.filter(id__in=[vehicle.id for vehicle in filtered_queryset])

        return queryset


class AutoFilter(BaseFilter):

    mileage_per_day = filters.RangeFilter(field_name='acceptable_mileage', label='Допустимый пробег/день')
    vehicle_class = filters.CharFilter(field_name='vehicle_class__slug', label='Класс транспорта')
    fuel_type = filters.CharFilter(field_name='fuel_type__slug', label='Тип топлива')
    seat_count = filters.RangeFilter(field_name='seats', label='Количество мест')
    transmission = filters.CharFilter(field_name='transmission__slug', label='Трансмиссия')
    body_type = filters.CharFilter(field_name='body_type__slug', label='Тип кузова')
    features_additionally = filters.ModelMultipleChoiceFilter(
        field_name='features_additionally__name',
        queryset=AutoFeaturesAdditionally.objects.all(),
        to_field_name='name',
        label='Выбор особенностей'
    )
    features_for_children = filters.ModelMultipleChoiceFilter(
        field_name='features_for_children__name',
        queryset=FeaturesForChildren.objects.all(),
        to_field_name='name',
        label='Для детей'
    )
    features_functions = filters.ModelMultipleChoiceFilter(
        field_name='features_functions__name',
        queryset=VehicleFeaturesFunctions.objects.all(),
        to_field_name='name',
        label='Функции'
    )
    class Meta:
        model = Auto
        fields = [
            'day_price', 'verified_only', 'mileage_per_day', 'rental_date', 'features_for_children', 'features_functions',
            'vehicle_class', 'features_additionally', 'fuel_type', 'brand', 'seat_count', 'transmission', 'year', 'super_host'
        ]


class BikeFilter(BaseFilter):
    mileage_per_day = filters.RangeFilter(field_name='acceptable_mileage', label='Допустимый пробег/день')
    vehicle_class = filters.CharFilter(field_name='vehicle_class__slug', label='Класс транспорта')
    engine_capacity = filters.RangeFilter(field_name='engine_capacity', label='Объем двигателя')
    seat_count = filters.RangeFilter(field_name='seat_count', label='Количество мест')
    transmission = filters.CharFilter(field_name='transmission__slug', label='Трансмиссия')
    features_additionally = filters.ModelMultipleChoiceFilter(
        field_name='features_additionally__name',
        queryset=BikeFeaturesAdditionally.objects.all(),
        to_field_name='name',
        label='Выбор особенностей'
    )
    features_functions = filters.ModelMultipleChoiceFilter(
        field_name='features_functions__name',
        queryset=VehicleFeaturesFunctions.objects.all(),
        to_field_name='name',
        label='Функции'
    )

    class Meta:
        model = Bike
        fields = [
            'day_price', 'super_host', 'mileage_per_day', 'rental_date', 'features_functions',
            'vehicle_class', 'features_additionally', 'engine_capacity', 'brand',
            'year', 'seat_count', 'transmission'
        ]


class ShipFilter(BaseFilter):
    mileage_per_day = filters.RangeFilter(field_name='acceptable_mileage', label='Допустимый пробег/день')
    vehicle_class = filters.CharFilter(field_name='vehicle_class__slug', label='Класс транспорта')
    engine_capacity = filters.RangeFilter(field_name='engine_capacity', label='Объем двигателя')
    type_ship = filters.CharFilter(field_name='type_ship', label='Тип транспорта')
    grot = filters.CharFilter(field_name='grot', label='Грот')
    features_additionally = filters.ModelMultipleChoiceFilter(
        field_name='features_additionally__name',
        queryset=ShipFeaturesAdditionally.objects.all(),
        to_field_name='name',
        label='Выбор особенностей'
    )
    features_functions = filters.ModelMultipleChoiceFilter(
        field_name='features_functions__name',
        queryset=VehicleFeaturesFunctions.objects.all(),
        to_field_name='name',
        label='Функции'
    )
    features_equipment = filters.ModelMultipleChoiceFilter(
        field_name='features_equipment__name',
        queryset=FeaturesEquipment.objects.all(),
        to_field_name='name',
        label='Оборудование'
    )

    class Meta:
        model = Ship
        fields = [
            'day_price', 'super_host', 'mileage_per_day', 'rental_date', 'features_functions', 'features_equipment',
            'vehicle_class', 'features_additionally', 'engine_capacity', 'brand', 'year', 'type_ship', 'grot']


class HelicopterFilter(BaseFilter):
    mileage_per_day = filters.RangeFilter(field_name='acceptable_mileage', label='Допустимый пробег/день')
    rental_date = filters.DateFromToRangeFilter(field_name='availabilities__start_date', label='Выбор даты аренды')
    vehicle_class = filters.CharFilter(field_name='vehicle_class__slug', label='Класс транспорта')
    engine_capacity = filters.RangeFilter(field_name='engine_capacity', label='Объем двигателя')
    max_speed = filters.RangeFilter(field_name='max_speed', label='Максимальная скорость, км/ч')
    full_take_weight = filters.RangeFilter(field_name='full_take_weight', label='Полный взлетный вес, кг')

    class Meta:
        model = Helicopter
        fields = [
            'day_price', 'super_host', 'mileage_per_day', 'rental_date', 'vehicle_class', 'engine_capacity', 'brand',
            'year', 'max_speed', 'full_take_weight']


class SpecialTechnicFilter(BaseFilter):
    type_technic = filters.RangeFilter(field_name='type_technic', label='Тип техники')
    engine_power = filters.RangeFilter(field_name='engine_power', label='Мощность двигателя, л.с.')
    operating_weight = filters.RangeFilter(field_name='operating_weight', label='Эксплутационная масса, кг')

    class Meta:
        model = SpecialTechnic
        fields = [
            'day_price', 'super_host', 'rental_date', 'brand',
            'year', 'type_technic', 'engine_power', 'operating_weight']


class VehicleModelFilter(filters.FilterSet):
    vehicle_type = filters.ChoiceFilter(choices=VehicleModel.VEHICLE_TYPES, label="Тип транспорта")

    class Meta:
        model = VehicleModel
        fields = ['vehicle_type']

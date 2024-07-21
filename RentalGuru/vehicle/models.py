from datetime import date

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from polymorphic.models import PolymorphicModel

from RentalGuru import settings
from chat.models import RequestRent


class VehicleBrand(models.Model):
    name = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='media/images/vehicle/brand_logo')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Марка'
        verbose_name_plural = 'Марки'


class VehicleModel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Модель'
        verbose_name_plural = 'Модели'


class VehicleFeaturesFunctions(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Функция'
        verbose_name_plural = 'Функции'


class AutoFeaturesAdditionally(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Дополнительная особенность, Автомобиль'
        verbose_name_plural = 'Дополнительные особенности, Автомобиль'


class BikeFeaturesAdditionally(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Дополнительная особенность, Мотоцикл'
        verbose_name_plural = 'Дополнительные особенности, Мотоцикл'


class ShipFeaturesAdditionally(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Дополнительная особенность, Судно'
        verbose_name_plural = 'Дополнительные особенности, Судно'


class FeaturesForChildren(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Для детей, Автомобиль'
        verbose_name_plural = 'Для детей, Автомобиль'


class FeaturesEquipment(models.Model):
    name = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Оборудование, Судно'
        verbose_name_plural = 'Оборудование, Судно'


class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Способ платежа'
        verbose_name_plural = 'Способы платежей'


def year_validate(value):
    if value < 1900 or value > timezone.now().year:
        raise ValidationError(f'Год выпуска должен быть в пределах 1900 и {timezone.now().year} года.')


def default_rating():
    rating = {
        "Cleanliness": {"5_stars": 0, "4_stars": 0, "3_stars": 0, "2_stars": 0, "1_stars": 0},
        "Maintenance": {"5_stars": 0, "4_stars": 0, "3_stars": 0, "2_stars": 0, "1_stars": 0},
        "Communication": {"5_stars": 0, "4_stars": 0, "3_stars": 0, "2_stars": 0, "1_stars": 0},
        "Convenience": {"5_stars": 0, "4_stars": 0, "3_stars": 0, "2_stars": 0, "1_stars": 0},
        "Accuracy": {"5_stars": 0, "4_stars": 0, "3_stars": 0, "2_stars": 0, "1_stars": 0},
    }
    return rating


class Vehicle(PolymorphicModel):
    request_rents = GenericRelation(RequestRent, related_query_name='request_rent')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicle', verbose_name='Владелец')
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='vehicle', verbose_name='Марка')
    model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='vehicle', verbose_name='Модель')
    year = models.IntegerField(null=True, blank=True, validators=[year_validate], verbose_name='Год выпуска')
    description = models.CharField(max_length=255, null=True, blank=True, verbose_name='Описание')
    long_distance = models.BooleanField(default=False, verbose_name='Междугородние поездки')
    delivery = models.BooleanField(default=False, verbose_name='Доставка')
    ensurance = models.CharField(max_length=30, verbose_name='Страховка')

    drivers_rating = models.DecimalField(null=True, blank=True, decimal_places=1, max_digits=2, verbose_name='Рейтинг арендатора')
    drivers_only_verified = models.BooleanField(default=True, verbose_name='Сдавать только верифицированным пользователям')

    price_delivery = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Стоимость доставки транспорта')
    price_deposit = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='депозит')
    min_rent_day = models.PositiveIntegerField(default=1, verbose_name='Минимальный срок аренды')
    max_rent_day = models.PositiveIntegerField(default=365, verbose_name='Максимальный срок аренды')

    payment_method = models.ManyToManyField(PaymentMethod, related_name='vehicles', verbose_name='Способ оплаты')

    location = models.CharField(max_length=255, verbose_name='Местоположение')
    ratings = models.JSONField(default=default_rating, verbose_name='Рейтинг транспорта')

    def update_free_dates(self, start_date, end_date):
        # Удаляем период доступности, который пересекается с поездкой
        availabilities = self.availabilities.filter(
            models.Q(start_date__lte=start_date, end_date__gte=start_date) |
            models.Q(start_date__lte=end_date, end_date__gte=end_date) |
            models.Q(start_date__gte=start_date, end_date__lte=end_date)
        )

        new_availabilities = []
        for availability in availabilities:
            if availability.start_date < start_date:
                new_availabilities.append(
                    Availability(vehicle=self, start_date=availability.start_date, end_date=start_date - date(1)))
            if availability.end_date > end_date:
                new_availabilities.append(
                    Availability(vehicle=self, start_date=end_date + date(1), end_date=availability.end_date))
            availability.delete()

        Availability.objects.bulk_create(new_availabilities)

    def get_average_rating(self):
        average_ratings = {}
        overall_total_stars = 0
        overall_total_ratings = 0

        for category, ratings in self.ratings.items():
            total_stars = sum(int(stars.split('_')[0]) * count for stars, count in ratings.items())
            total_ratings = sum(ratings.values())
            average_rating = total_stars / total_ratings if total_ratings > 0 else 0
            average_ratings[category] = average_rating
            overall_total_stars += total_stars
            overall_total_ratings += total_ratings

        overall_average = overall_total_stars / overall_total_ratings if overall_total_ratings > 0 else 0
        average_ratings['rating'] = overall_average

        return average_ratings

    def __str__(self):
        return f'Vehicle id-{self.pk}'


class RentPrice(models.Model):
    RENT_PERIOD = (
        ('day', 'День'),
        ('week', 'Неделя'),
        ('month', 'Месяц'),
        ('year', 'Год'),
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='rent_prices')
    name = models.CharField(choices=RENT_PERIOD, max_length=5, verbose_name='Период')
    price = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Стоимость')
    commission = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Комиссия')
    discount = models.PositiveIntegerField(default=0, verbose_name='Скидка')
    total = models.DecimalField(decimal_places=2, max_digits=10, verbose_name='ИТОГО')

    def save(self, *args, **kwargs):
        self.total = (float(self.price) + float(self.commission)) * (100 - float(self.discount)) / 100
        super(RentPrice, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Период'
        verbose_name_plural = 'Стоимость аренды'
        unique_together = ('vehicle', 'name')


class Availability(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='availabilities')
    start_date = models.DateField(verbose_name='Начало')
    end_date = models.DateField(verbose_name='Конец')

    def __str__(self):
        return f'Availability {self.start_date} to {self.end_date}'

    class Meta:
        verbose_name = 'Дата аренды'
        verbose_name_plural = 'Даты аренды'


def vehicle_documents_upload_to(instance, filename):
    vehicle_type = instance.vehicle._meta.model_name
    return f'media/images/vehicles/{vehicle_type}/{instance.vehicle.id}/documents/{filename}'


class VehicleDocument(models.Model):
    name = models.CharField(max_length=50, verbose_name='Вид документа')
    image = models.ImageField(upload_to=vehicle_documents_upload_to, verbose_name='Фото документа')
    number = models.IntegerField(verbose_name='Номер')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'


def vehicle_photo_upload_to(instance, filename):
    vehicle_type = instance.vehicle._meta.model_name
    return f'media/images/vehicles/{vehicle_type}/{instance.vehicle.id}/{filename}'


class VehiclePhoto(models.Model):
    vehicle = models.ForeignKey('Vehicle', related_name='photos', on_delete=models.CASCADE)
    photo = models.ImageField(upload_to=vehicle_photo_upload_to, verbose_name='Фото')

    def __str__(self):
        return f'Photo for vehicle id-{self.vehicle.pk}'

    class Meta:
        verbose_name = 'Фото'
        verbose_name_plural = 'Фото'


class Auto(Vehicle):
    FUEL_CHOICES = (
        ('electric', 'Электричество'),
        ('hybrid', 'Гибрид'),
        ('petrol', 'Бензин'),
        ('diesel', 'Дизель'),
    )
    CLASS_CHOICES = (
        ('business', 'Бизнес'),
        ('premium', 'Премиум'),
        ('casual', 'Средний')
    )
    TRANSMISSION_CHOICES = (
        ('automatic', 'Автоматическая'),
        ('robot', 'Робот'),
        ('variator', 'Вариатор'),
        ('manual', 'Механическая'),
    )
    BODY_CHOICES = (
        ('automatic', 'Седан'),
        ('off-road', 'Внедорожник'),
        ('universal', 'Универсал'),
        ('hatchback', 'Хэтчбэк'),
        ('compartment', 'Купэ'),
        ('minivan', 'Минивэн'),
        ('minibus', 'Микроавтобус'),
        ('liftback', 'Лифтбэк'),
        ('pickup', 'Пикап'),
        ('van', 'Фургон'),
        ('convertible', 'Кабриолет')
    )

    transmission = models.CharField(max_length=12, choices=TRANSMISSION_CHOICES, verbose_name='Коробка передач')
    fuel_type = models.CharField(max_length=13, choices=FUEL_CHOICES, verbose_name='Вид топлива')
    body_type = models.CharField(max_length=13, choices=BODY_CHOICES, verbose_name='Тип кузова')

    acceptable_mileage = models.IntegerField(verbose_name='Допустимый пробег, день')
    seats = models.PositiveIntegerField(default=4, verbose_name='Количество мест')
    vehicle_class = models.CharField(max_length=8, choices=CLASS_CHOICES, verbose_name='Класс')

    drivers_age = models.PositiveIntegerField(null=True, blank=True, verbose_name='Возраст водителя')
    drivers_experience = models.PositiveIntegerField(null=True, blank=True, verbose_name='Стаж водителя')

    features_for_children = models.ManyToManyField(FeaturesForChildren, related_name='auto', blank=True, verbose_name='Для детей')
    features_functions = models.ManyToManyField(VehicleFeaturesFunctions, related_name='auto', blank=True, verbose_name='Функции')
    features_additionally = models.ManyToManyField(AutoFeaturesAdditionally, related_name='auto', blank=True, verbose_name='Дополнительно')

    def __str__(self):
        return f'Автомобиль {self.brand.name} {self.model.name}'

    def clean(self):
        if self.seats and (self.seats < 1 or self.seats > 10):
            raise ValidationError({'seats': 'Seats must be between 1 and 10.'})

    class Meta:
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили'


class Bike(Vehicle):
    CLASS_CHOICES = (
        ('premium', 'Премиум'),
        ('comfort', 'Комфорт'),
        ('casual', 'Эконом')
    )
    TRANSMISSION_CHOICES = (
        ('automatic', 'Автоматическая'),
        ('manual', 'Механическая'),
    )

    transmission = models.CharField(max_length=12, choices=TRANSMISSION_CHOICES, verbose_name='Коробка передач')
    engine_capacity = models.IntegerField(null=True, blank=True, verbose_name='Объем двигателя')
    seats = models.PositiveIntegerField(default=2, verbose_name='Количество мест')
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES, verbose_name='Класс')
    acceptable_mileage = models.IntegerField(verbose_name='Допустимый пробег, день')

    drivers_age = models.PositiveIntegerField(null=True, blank=True, verbose_name='Возраст водителя')
    drivers_experience = models.PositiveIntegerField(null=True, blank=True, verbose_name='Стаж водителя')

    features_functions = models.ManyToManyField(VehicleFeaturesFunctions, related_name='bike', verbose_name='Функции')
    features_additionally = models.ManyToManyField(BikeFeaturesAdditionally, related_name='bike', verbose_name='Допольнительно')

    def __str__(self):
        return f'Мотоцикл {self.brand.name} {self.model.name}'

    def clean(self):
        if self.seats and (self.seats < 1 or self.seats > 4):
            raise ValidationError({'seats': 'Seats must be between 1 and 4.'})

    class Meta:
        verbose_name = 'Мотоцикл'
        verbose_name_plural = 'Мотоциклы'


class Ship(Vehicle):
    CLASS_CHOICES = (
        ('premium', 'Премиум'),
        ('comfort', 'Комфорт'),
        ('casual', 'Эконом')
    )

    type_ship = models.CharField(null=True, blank=True, verbose_name='Тип транспорта')
    grot = models.CharField(null=True, blank=True, verbose_name='Грот')
    length = models.FloatField(null=True, blank=True, verbose_name='Длина, м')
    width = models.FloatField(null=True, blank=True, verbose_name='Ширина, м')
    precipitation = models.FloatField(null=True, blank=True, verbose_name='Осадка, м')
    seats = models.PositiveIntegerField(default=2, verbose_name='Количество мест')
    sleeping_place = models.PositiveIntegerField(null=True, blank=True, verbose_name='Спальных мест')
    one_sleeping_place = models.PositiveIntegerField(null=True, blank=True, verbose_name='1-спальных кают')
    two_sleeping_place = models.PositiveIntegerField(null=True, blank=True, verbose_name='2-спальных кают')
    toilet = models.PositiveIntegerField(null=True, blank=True, verbose_name='Туалетов')
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES, verbose_name='Класс')
    engine_capacity = models.IntegerField(null=True, blank=True, verbose_name='Объем двигателя')
    water_tank = models.IntegerField(null=True, blank=True, verbose_name='Бак для воды, л')
    fuel_tank = models.IntegerField(null=True, blank=True, verbose_name='Топливный бак, л')
    acceptable_mileage = models.IntegerField(verbose_name='Допустимый пробег, день')

    features_functions = models.ManyToManyField(VehicleFeaturesFunctions, related_name='ship', verbose_name='Функции')
    features_additionally = models.ManyToManyField(ShipFeaturesAdditionally, related_name='ship', verbose_name='Допольнительно')
    features_equipment = models.ManyToManyField(FeaturesEquipment, related_name='ship', verbose_name='Оборудование')

    def __str__(self):
        return f'Судно {self.brand.name} {self.model.name}'

    class Meta:
        verbose_name = 'Судно'
        verbose_name_plural = 'Судна'


class Helicopter(Vehicle):
    CLASS_CHOICES = (
        ('premium', 'Премиум'),
        ('comfort', 'Комфорт'),
        ('casual', 'Эконом')
    )

    max_speed = models.IntegerField(null=True, blank=True, verbose_name='Максимальная скорость, км/ч')
    cruising_speed = models.IntegerField(null=True, blank=True, verbose_name='Крейсерская скорость, км/ч')
    flight_range = models.IntegerField(null=True, blank=True, verbose_name='Дальность полета,км')
    flight_duration = models.IntegerField(null=True, blank=True, verbose_name='Длительность полета, ч')

    power_cruising = models.IntegerField(null=True, blank=True, verbose_name='Мощность, крейсерская, л.с.')
    take_off_power = models.IntegerField(null=True, blank=True, verbose_name='Мощность взлетная, л.с.')
    full_take_weight = models.IntegerField(null=True, blank=True, verbose_name='Полный взлетный вес, кг')
    payload = models.IntegerField(verbose_name='Полезная нагрузка, кг')
    engine_capacity = models.IntegerField(null=True, blank=True, verbose_name='Объем двигателя')
    fuel_tank = models.IntegerField(null=True, blank=True, verbose_name='Объем топливного бака, л.')
    acceptable_mileage = models.IntegerField(verbose_name='Допустимый пробег, день')
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES, verbose_name='Класс')

    def __str__(self):
        return f'Вертолет {self.brand.name} {self.model.name}'

    class Meta:
        verbose_name = 'Вертолет'
        verbose_name_plural = 'Вертолеты'


class SpecialTechnic(Vehicle):
    type_technic = models.CharField(null=True, blank=True, verbose_name='Тип техники')
    engine_power = models.IntegerField(null=True, blank=True, verbose_name='Мощность двигателя, л.с.')
    length = models.FloatField(null=True, blank=True, verbose_name='Длина, м')
    width = models.FloatField(null=True, blank=True, verbose_name='Ширина, м')
    high = models.FloatField(null=True, blank=True, verbose_name='Высота, м')
    operating_weight = models.IntegerField(verbose_name='Эксплутационная масса, кг')

    def __str__(self):
        return f'Спец техника {self.brand.name} {self.model.name}'

    class Meta:
        verbose_name = 'Спец техника'
        verbose_name_plural = 'Спец техника'

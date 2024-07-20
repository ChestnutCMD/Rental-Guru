from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from polymorphic.models import PolymorphicModel

from RentalGuru import settings


class VehicleBrand(models.Model):
    name = models.CharField(max_length=50, unique=True)
    logo = models.ImageField(upload_to='media/images/brand_logo')

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


class Vehicle(PolymorphicModel):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicle')
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE, related_name='vehicle')
    model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='vehicle')
    year = models.IntegerField(null=True, blank=True)  # Год выпуска транспорта
    description = models.CharField(max_length=255, null=True, blank=True)
    long_distance = models.BooleanField(default=False)  # Междугородние поездки
    delivery = models.BooleanField(default=False)  # Доставка транспорта
    ensurance = models.CharField(max_length=30)  # Страховка

    drivers_rating = models.DecimalField(null=True, blank=True, decimal_places=1, max_digits=2)  # Условия аренды
    drivers_only_verified = models.BooleanField(default=True)  # Условия аренды

    price_delivery = models.DecimalField(decimal_places=2, max_digits=10)  #
    price_deposit = models.DecimalField(decimal_places=2, max_digits=10)  #
    min_rent_day = models.PositiveIntegerField(default=1)  #
    max_rent_day = models.PositiveIntegerField(default=365)  #

    payment_method = models.ManyToManyField(PaymentMethod, related_name='vehicles')  # Способ оплаты

    location = models.CharField(max_length=255)

    photo = models.ImageField(upload_to='media/images/vehicles/')

    ratings = models.JSONField(default=dict)

    def clean(self):
        current_year = timezone.now().year
        if self.year and (self.year < 1900 or self.year > current_year):
            raise ValidationError({'year': f'Year must be between 1900 and {current_year}.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

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
    name = models.CharField(choices=RENT_PERIOD, max_length=5)
    price = models.DecimalField(decimal_places=2, max_digits=10)
    commission = models.DecimalField(decimal_places=2, max_digits=10)
    discount = models.PositiveIntegerField(default=0)
    total = models.DecimalField(decimal_places=2, max_digits=10)

    def save(self, *args, **kwargs):
        self.total = (float(self.price) + float(self.commission)) * (100 - float(self.discount)) / 100
        super(RentPrice, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Стоимость аренды'
        verbose_name_plural = 'Стоимость аренды'
        unique_together = ('vehicle', 'name')


class Availability(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='availabilities')
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f'Availability {self.start_date} to {self.end_date}'


class VehicleDocument(models.Model):
    name = models.CharField(max_length=50)
    image = models.ImageField(upload_to=f'media/images/vehicle/')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='documents')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'


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

    transmission = models.CharField(max_length=12, choices=TRANSMISSION_CHOICES)
    fuel_type = models.CharField(max_length=13, choices=FUEL_CHOICES)
    body_type = models.CharField(max_length=13, choices=BODY_CHOICES)

    acceptable_mileage = models.IntegerField()  # Допустимый пробег в день
    seats = models.PositiveIntegerField(default=4)
    vehicle_class = models.CharField(max_length=8, choices=CLASS_CHOICES)

    drivers_age = models.PositiveIntegerField(null=True, blank=True)
    drivers_experience = models.PositiveIntegerField(null=True, blank=True)

    features_for_children = models.ManyToManyField(FeaturesForChildren, related_name='auto', blank=True)  # Для детей
    features_functions = models.ManyToManyField(VehicleFeaturesFunctions, related_name='auto', blank=True)  # Функции
    features_additionally = models.ManyToManyField(AutoFeaturesAdditionally, related_name='auto', blank=True)  # Дополнительно

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

    transmission = models.CharField(max_length=12, choices=TRANSMISSION_CHOICES)
    engine_capacity = models.IntegerField(null=True, blank=True)
    seats = models.PositiveIntegerField(default=2)
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES)
    acceptable_mileage = models.IntegerField()  # Допустимый пробег в день

    drivers_age = models.PositiveIntegerField(null=True, blank=True)
    drivers_experience = models.PositiveIntegerField(null=True, blank=True)

    features_functions = models.ManyToManyField(VehicleFeaturesFunctions, related_name='bike')  # Функции
    features_additionally = models.ManyToManyField(BikeFeaturesAdditionally, related_name='bike')  # Допольнительно

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

    type_ship = models.CharField(null=True, blank=True)
    grot = models.CharField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    precipitation = models.FloatField(null=True, blank=True)
    seats = models.PositiveIntegerField(default=2)
    sleeping_place = models.PositiveIntegerField(null=True, blank=True)
    one_sleeping_place = models.PositiveIntegerField(null=True, blank=True)
    two_sleeping_place = models.PositiveIntegerField(null=True, blank=True)
    toilet = models.PositiveIntegerField(null=True, blank=True)
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES)
    engine_capacity = models.IntegerField(null=True, blank=True)
    water_tank = models.IntegerField(null=True, blank=True)
    fuel_tank = models.IntegerField(null=True, blank=True)
    acceptable_mileage = models.IntegerField()  # Допустимый пробег в день

    features_functions = models.ManyToManyField(VehicleFeaturesFunctions, related_name='ship')  # Функции
    features_additionally = models.ManyToManyField(ShipFeaturesAdditionally, related_name='ship')  # Допольнительно
    features_equipment = models.ManyToManyField(FeaturesEquipment, related_name='ship')  # Оборудование

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

    max_speed = models.IntegerField(null=True, blank=True)
    cruising_speed = models.IntegerField(null=True, blank=True)
    flight_range = models.IntegerField(null=True, blank=True)
    flight_duration = models.IntegerField(null=True, blank=True)

    power_cruising = models.IntegerField(null=True, blank=True)
    take_off_power = models.IntegerField(null=True, blank=True)
    full_take_weight = models.IntegerField(null=True, blank=True)
    payload = models.IntegerField()
    engine_capacity = models.IntegerField(null=True, blank=True)
    fuel_tank = models.IntegerField(null=True, blank=True)
    acceptable_mileage = models.IntegerField()  # Допустимый пробег в день
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES)

    def __str__(self):
        return f'Вертолет {self.brand.name} {self.model.name}'

    class Meta:
        verbose_name = 'Вертолет'
        verbose_name_plural = 'Вертолеты'


class SpecialTechnic(Vehicle):
    type_technic = models.CharField(null=True, blank=True)
    engine_power = models.IntegerField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    high = models.FloatField(null=True, blank=True)
    operating_weight = models.IntegerField()

    def __str__(self):
        return f'Спец техника {self.brand.name} {self.model.name}'

    class Meta:
        verbose_name = 'Спец техника'
        verbose_name_plural = 'Спец техника'

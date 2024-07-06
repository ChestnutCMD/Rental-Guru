from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from app.models import User


class VehicleBrand(models.Model):
    name = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='brand_logo')


class VehicleModel(models.Model):
    name = models.CharField(max_length=50)
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE)


class Vehicle(models.Model):
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    brand = models.ForeignKey(VehicleBrand, null=True, on_delete=models.SET_NULL)
    model = models.ForeignKey(VehicleModel, null=True, on_delete=models.SET_NULL)
    year = models.IntegerField(null=True, blank=True)
    features = models.JSONField(default=dict)
    long_distance = models.BooleanField(default=False)
    delivery = models.BooleanField(default=False)
    ensurance = models.CharField(max_length=30)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    available_from = models.DateField()
    available_to = models.DateField()

    acceptable_mileage = models.IntegerField(null=True, blank=True)
    photo = models.ImageField(upload_to='vehicles/')

    ratings = models.JSONField(default={
        "purity": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "service": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "communication": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "convenience": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "accuracy": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0}
    })

    def clean(self):
        current_year = timezone.now().year
        if self.year and (self.year < 1900 or self.year > current_year):
            raise ValidationError({'year': f'Year must be between 1900 and {current_year}.'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class Auto(Vehicle):
    FUEL_CHOICES = (
        ('electric', 'Электричество'),
        ('hybrid', 'Гибрид'),
        ('petrol', 'Бензин'),
        ('diesel', 'Дизель'),
    )
    CLASS_CHOICES = (
        ('premium', 'Премиум'),
        ('comfort', 'Комфорт'),
        ('casual', 'Эконом')
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

    seats = models.PositiveIntegerField(default=2)
    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES)

    def __str__(self):
        return f'Автомобиль {self.brand.name} {self.model.name}'

    def clean(self):
        if self.seats and (self.seats < 1 or self.seats > 10):
            raise ValidationError({'seats': 'Seats must be between 1 and 10.'})


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

    def __str__(self):
        return f'Мотоцикл {self.brand.name} {self.model.name}'

    def clean(self):
        if self.seats and (self.seats < 1 or self.seats > 4):
            raise ValidationError({'seats': 'Seats must be between 1 and 4.'})


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

    def __str__(self):
        return f'Судно {self.brand.name} {self.model.name}'


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

    vehicle_class = models.CharField(max_length=7, choices=CLASS_CHOICES)

    def __str__(self):
        return f'Вертолет {self.brand.name} {self.model.name}'


class SpecialTechnic(Vehicle):

    type_technic = models.CharField(null=True, blank=True)
    engine_power = models.IntegerField(null=True, blank=True)
    length = models.FloatField(null=True, blank=True)
    width = models.FloatField(null=True, blank=True)
    high = models.FloatField(null=True, blank=True)
    operating_weight = models.IntegerField()

    def __str__(self):
        return f'Спец техника {self.brand.name} {self.model.name}'

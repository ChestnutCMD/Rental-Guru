from django.db import models

from app.models import User


class VehicleType(models.Model):
    name = models.CharField(max_length=20)


class VehicleBrand(models.Model):
    name = models.CharField(max_length=50)
    logo = models.ImageField(upload_to='brand_logo')


class VehicleModel(models.Model):
    name = models.CharField(max_length=50)
    brand = models.ForeignKey(VehicleBrand, on_delete=models.CASCADE)


class Vehicle(models.Model):
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
    type = models.ForeignKey(VehicleType, null=True, on_delete=models.SET_NULL)
    owner = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    brand = models.ForeignKey(VehicleBrand, null=True, on_delete=models.SET_NULL)
    model = models.ForeignKey(VehicleModel, null=True, on_delete=models.SET_NULL)
    year = models.IntegerField(null=True, blank=True)
    transmission = models.CharField(max_length=4, null=True, blank=True)
    fuel_type = models.CharField(max_length=10, choices=FUEL_CHOICES)
    features = models.JSONField(default=dict)
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    available_from = models.DateField()
    available_to = models.DateField()
    seats = models.PositiveIntegerField(null=True, blank=True)
    locations = models.CharField(max_length=255)
    photo = models.ImageField(upload_to='vehicles/')
    vehicle_class = models.CharField(max_length=10, choices=CLASS_CHOICES)
    ratings = models.JSONField(default={
        "purity": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "service": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "communication": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "convenience": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0},
        "accuracy": {"one_star": 0, "two_star": 0, "three_star": 0, "four_star": 0, "five_star": 0}
    })

    def __str__(self):
        return f'{self.brand.name} {self.model.name}'

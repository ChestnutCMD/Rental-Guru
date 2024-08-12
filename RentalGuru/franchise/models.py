from django.db import models

from RentalGuru import settings


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name='Категория')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'


class Franchise(models.Model):
    name = models.CharField(max_length=50, verbose_name='Имя компании')
    unn = models.CharField(max_length=12, unique=True, verbose_name='УНН')
    date_register = models.DateField(auto_now_add=True, verbose_name='Дата регистрации')
    telephone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(max_length=50, verbose_name='Эл. почта')
    country = models.CharField(max_length=50, verbose_name='Страна')
    city = models.CharField(max_length=50, verbose_name='Город')

    director = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Директор')
    commission = models.PositiveIntegerField(default=3, verbose_name='Комиссия')

    categories = models.ManyToManyField(Category, related_name='franchises', verbose_name='Категории')
    verified = models.BooleanField(default=False, verbose_name='Верифицировано')

    def __str__(self):
        return f"{self.name} ({self.country}, {self.city})"

    class Meta:
        verbose_name = 'Франшиза'
        verbose_name_plural = 'Франшизы'


class VehiclePark(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название автопарка')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicle_park', verbose_name='Автопарк')

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name = 'Автопарк'
        verbose_name_plural = 'Автопарки'

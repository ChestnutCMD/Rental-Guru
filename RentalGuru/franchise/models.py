from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

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
    total_vehicles = models.PositiveIntegerField(default=0, verbose_name='Общее количество транспортных средств')
    categories = models.ManyToManyField(Category, related_name='franchises', verbose_name='Категории')

    def update_total_vehicles(self):
        from vehicle.models import Vehicle
        vehicles_in_parks = sum(park.vehicles.count() for park in self.vehicle_parks.all())
        unassigned_vehicles_count = Vehicle.objects.filter(franchise=self, vehicle_park__isnull=True).count()
        self.total_vehicles = vehicles_in_parks + unassigned_vehicles_count

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_total_vehicles()
        super().save(update_fields=['total_vehicles'])

    def __str__(self):
        return f"{self.name} ({self.country}, {self.city})"

    class Meta:
        verbose_name = 'Франшиза'
        verbose_name_plural = 'Франшизы'


class VehiclePark(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название автопарка')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicle_parks', verbose_name='Автопарк')
    franchise = models.ForeignKey(Franchise, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_parks', verbose_name='Франшиза')

    def __str__(self):
        return str(self.name)

    @receiver(post_delete, sender=Franchise)
    def delete_related_vehicles(sender, instance, **kwargs):
        VehiclePark.objects.filter(franchise=instance).delete()

    class Meta:
        verbose_name = 'Автопарк'
        verbose_name_plural = 'Автопарки'


class RequestFranchise(models.Model):
    name = models.CharField(max_length=50, verbose_name='Имя компании')
    telephone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(max_length=50, verbose_name='Эл. почта')
    city = models.CharField(max_length=50, verbose_name='Город')

    class Meta:
        verbose_name = 'Заявка на франшизу'
        verbose_name_plural = 'Заявки на франшизы'

    def __str__(self):
        return f'Имя: {self.name}, телефон: {self.telephone}'

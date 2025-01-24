from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q, Sum
from django.db.models.signals import post_delete
from django.dispatch import receiver
from rest_framework.exceptions import ValidationError

from RentalGuru import settings
from chat.models import Trip


class City(models.Model):
    title = models.CharField(max_length=50, unique=True, verbose_name='Город')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'


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
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, verbose_name='Город')

    director = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Директор')
    commission = models.PositiveIntegerField(default=3, verbose_name='Комиссия')
    total_vehicles = models.PositiveIntegerField(default=0, verbose_name='Общее количество транспортных средств')
    categories = models.ManyToManyField(Category, related_name='franchises', verbose_name='Категории')

    def save_total_vehicles(self):
        self.total_vehicles = self.get_total_vehicles()
        self.save(update_fields=['total_vehicles'])

    def get_vehicles(self):
        from vehicle.models import Vehicle
        return Vehicle.objects.filter(
            Q(owner__lessor__franchise=self) | Q(owner=self.director)
        )

    def get_total_vehicles(self):
        return self.get_vehicles().count()

    def get_total_revenue(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id'),
            status='finished'
        ).aggregate(total_revenue=Sum('total_cost'))['total_revenue'] or 0.00

    def get_total_margin(self):
        revenue = Decimal(self.get_total_revenue())
        commission_decimal = Decimal(self.commission) / 100
        return revenue * (1 - commission_decimal)

    def get_total_orders(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id')
        ).count()

    def get_royalty(self):
        revenue = Decimal(self.get_total_revenue())
        return (revenue/100) * Decimal(self.commission)

    def get_total_completed_orders(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id'),
            status='finished'
        ).count()

    def get_total_cancelled_orders(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id'),
            status='canceled'
        ).count()

    def get_active_users_count(self):
        from app.models import User
        return User.objects.filter(
            lessor__franchise=self
        ).count()

    def get_statistics(self):
        return {
            'total_vehicles': self.get_total_vehicles(),
            'total_revenue': self.get_total_revenue(),
            'total_margin': self.get_total_margin(),
            'total_orders': self.get_total_orders(),
            'total_completed_orders': self.get_total_completed_orders(),
            'total_cancelled_orders': self.get_total_cancelled_orders(),
            'royalty': self.get_royalty(),
            'active_users_count': self.get_active_users_count(),
        }

    def __str__(self):
        return f"{self.name} ({self.country}, {self.city})"

    def clean(self):
        if self.city and Franchise.objects.filter(city=self.city).exclude(id=self.id).exists():
            raise ValidationError(f'Для города {self.city} уже зарегистрирована франшиза.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Франшиза'
        verbose_name_plural = 'Франшизы'


class VehiclePark(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название автопарка')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicle_parks', verbose_name='Автопарк')
    franchise = models.ForeignKey(Franchise, on_delete=models.SET_NULL, null=True, blank=True, related_name='vehicle_parks', verbose_name='Франшиза')

    class Meta:
        verbose_name = 'Автопарк'
        verbose_name_plural = 'Автопарки'

    def __str__(self):
        return str(self.name)

    @receiver(post_delete, sender=Franchise)
    def delete_related_vehicles(sender, instance, **kwargs):
        VehiclePark.objects.filter(franchise=instance).delete()

    def get_vehicles(self):
        """Метод для получения всех транспортных средств, связанных с данным автопарком."""
        from vehicle.models import Vehicle
        return Vehicle.objects.filter(vehicle_park=self)

    def get_total_vehicles(self):
        return self.get_vehicles().count()

    def get_total_revenue(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id'),
            status='finished'
        ).aggregate(total_revenue=Sum('total_cost'))['total_revenue'] or 0.00

    def get_total_orders(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id')
        ).count()

    def get_total_completed_orders(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id'),
            status='finished'
        ).count()

    def get_total_cancelled_orders(self):
        return Trip.objects.filter(
            content_type__in=ContentType.objects.filter(
                model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic']),
            object_id__in=self.get_vehicles().values('id'),
            status='canceled'
        ).count()

    def get_statistics(self):
        return {
            'total_vehicles': self.get_total_vehicles(),
            'total_revenue': self.get_total_revenue(),
            'total_orders': self.get_total_orders(),
            'total_completed_orders': self.get_total_completed_orders(),
            'total_cancelled_orders': self.get_total_cancelled_orders(),
        }


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

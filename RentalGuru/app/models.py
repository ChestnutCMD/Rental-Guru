from django.contrib.auth.models import AbstractUser
from django.db import models

from app.manager import UserManager
from vehicle.models import Vehicle


def upload_avatar(instance, filename):
    return f'media/images/users/{instance.id}/avatar/{filename}'


class User(AbstractUser):
    ROLES = (
        ('member', 'Пользователь'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='member', verbose_name='Роль')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    telephone = models.CharField(max_length=11, null=True, blank=True, verbose_name='Телефон')
    currency = models.CharField(max_length=3, null=True, blank=True, verbose_name='Валюта')
    avatar = models.ImageField(upload_to=upload_avatar, null=True, blank=True, verbose_name='Аватар')
    about = models.TextField(null=True, blank=True, verbose_name='О себе')
    email_notification = models.BooleanField(default=False, verbose_name='Email уведомления')
    push_notification = models.BooleanField(default=False, verbose_name='Push уеведомления')

    first_name = models.CharField(null=True, max_length=150, blank=True, verbose_name='Имя')
    last_name = models.CharField(null=True, max_length=150, blank=True, verbose_name='Фамилия')

    email = models.EmailField(unique=True, verbose_name='Email')
    username = None
    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Lessor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='lessor')
    super_host = models.BooleanField(default=False, verbose_name='Суперхост')
    count_trip = models.PositiveIntegerField(default=0, verbose_name='Колличество поездок')
    average_response_time = models.TimeField(null=True, blank=True, verbose_name='Среднее время ответа')

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = 'Арендодатель'
        verbose_name_plural = 'Арендодатели'


class Renter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='renter')
    favorite = models.ManyToManyField(Vehicle, blank=True, verbose_name='Избранное')
    verification = models.BooleanField(default=False, verbose_name='Верифированный пользователь')

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = 'Арендатор'
        verbose_name_plural = 'Арендаторы'


def upload_renter_document(instance, filename):
    return f'media/images/users/{instance.renter.user.id}/documents/{filename}'


class RenterDocuments(models.Model):
    renter = models.ForeignKey(Renter, related_name='renter_documents', on_delete=models.CASCADE)
    title = models.CharField(max_length=30, verbose_name='Вид документа')
    number = models.PositiveIntegerField(verbose_name='Номер')
    photo = models.ImageField(upload_to=upload_renter_document, verbose_name='Фото')

    def __str__(self):
        return f'{self.title}: {self.number}'

    class Meta:
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

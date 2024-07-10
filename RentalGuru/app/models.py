from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = (
        ('member', 'Пользователь'),
        ('manager', 'Менеджер'),
        ('admin', 'Администратор'),
    )
    role = models.CharField(max_length=10, choices=ROLES, default='member')
    date_of_birth = models.DateField(null=True, blank=True)
    telephone = models.CharField(max_length=11, null=True, blank=True)
    currency = models.CharField(max_length=3, null=True, blank=True)
    avatar = models.ImageField(upload_to='images/avatars/', null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    email_notification = models.BooleanField(default=False)
    push_notification = models.BooleanField(default=False)

    email = models.EmailField(unique=True)
    username = None

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Lessor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    super_host = models.BooleanField(default=False)
    count_trip = models.PositiveIntegerField(default=0)
    average_response_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return self.user


class Renter(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user

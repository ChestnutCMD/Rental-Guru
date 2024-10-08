from django.core.exceptions import ValidationError
from django.db import models

from app.models import User
from vehicle.models import Vehicle


class Complaint(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name='Пользователь')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, verbose_name='Транспорт')
    topic = models.CharField(max_length=50, null=True, blank=True, verbose_name='Причина жалобы')
    description = models.CharField(max_length=250, null=True, blank=True, verbose_name='Описание')

    def clean(self):
        if not self.topic and not self.description:
            raise ValidationError('Описание обязательно, если причина жалобы не указана.')

    def __str__(self):
        if self.topic:
            return str(self.topic)
        return f"{self.description[0:30]}..."

    class Meta:
        unique_together = ('user', 'vehicle')
        verbose_name = 'Жалоба'
        verbose_name_plural = 'Жалобы'

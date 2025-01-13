from datetime import timedelta

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError

from RentalGuru import settings


class Manager(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='manager')
    password_updated_at = models.DateTimeField(default=now, verbose_name="Дата изменения пароля")

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def check_password_expiry(self):
        if not self.password_updated_at:
            return "Пароль никогда не обновлялся. Рекомендуем сменить пароль."
        if self.password_updated_at + timedelta(days=30) < timezone.now():
            return "Пароль устарел. Пожалуйста, обновите пароль."
        return None

    class Meta:
        verbose_name = 'Менеджер'
        verbose_name_plural = 'Менеджеры'


def upload_manager_document(instance, filename):
    return f'media/images/users/{instance.manager.user.id}/documents/{filename}'


class ManagerDocuments(models.Model):
    manager = models.OneToOneField(Manager, related_name='manager_document', on_delete=models.CASCADE, verbose_name='Менеджер')
    number = models.CharField(max_length=50, verbose_name='Серия и номер')
    photo = models.ImageField(upload_to=upload_manager_document, verbose_name='Фото')

    def __str__(self):
        return self.number

    class Meta:
        verbose_name = 'Паспортные данные'
        verbose_name_plural = 'Паспортные данные'


class ManagerPermission(models.Model):
    """
    Модель для управления доступами менеджеров к объектам.
    """
    manager = models.ForeignKey("Manager", on_delete=models.CASCADE, related_name="permissions")
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="Тип модели")
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID объекта")
    content_object = GenericForeignKey("content_type", "object_id")
    permission_type = models.CharField(
        max_length=50,
        choices=[
            ('read', 'Чтение'),
            ('edit', 'Редактирование'),
            ('delete', 'Удаление'),
        ],
        verbose_name="Тип доступа",
    )
    is_global = models.BooleanField(default=False, verbose_name="Глобальный доступ")

    class Meta:
        unique_together = ('manager', 'content_type', 'object_id', 'permission_type', 'is_global')
        verbose_name = "Права менеджера"
        verbose_name_plural = "Права менеджеров"

    def __str__(self):
        if self.is_global:
            return f"{self.manager.user} — {self.permission_type} на все объекты {self.content_type.model}"
        return f"{self.manager.user} — {self.permission_type} на объект {self.content_type.model} ID {self.object_id}"

    def clean(self):
        """
        Валидация модели перед сохранением.
        """
        if not self.content_type:
            raise ValidationError({
                'content_type': "content_type обязателен для указания модели."
            })

        if self.is_global:
            if self.object_id is not None:
                raise ValidationError({
                    'object_id': "object_id должно быть пустым для глобального доступа."
                })
        else:
            if self.object_id is None:
                raise ValidationError({
                    'object_id': "object_id обязателен для локального доступа."
                })
        super().clean()

    def save(self, *args, **kwargs):
        """
        Вызываем clean перед сохранением.
        """
        self.clean()
        super().save(*args, **kwargs)

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from RentalGuru import settings


class RequestRent(models.Model):
    STATUS_CHOICES = (
        ('accept', 'Принять'),
        ('denied', 'Отказать'),
        ('unknown', 'Не рассмотренно')
    )
    status = models.CharField(max_length=7, default='unknown', choices=STATUS_CHOICES, verbose_name='Статус')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='request_rent_organized_trips', verbose_name='Автор')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_date = models.DateField(verbose_name='Начало аренды')
    end_date = models.DateField(verbose_name='Конец аренды')

    @property
    def owner(self):
        return self.vehicle.owner

    def __str__(self):
        return f'request rent id-{self.pk}'

    class Meta:
        verbose_name = 'Заявка на аренду'
        verbose_name_plural = 'Заявки на аренду'


class Trip(models.Model):
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trip_organized_trips', verbose_name='Организатор')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_date = models.DateField(verbose_name='Начало поездки')
    end_date = models.DateField(verbose_name='Конец поездки')

    @property
    def owner(self):
        return self.vehicle.owner

    def __str__(self):
        return f'Поездка id-{self.pk}'

    class Meta:
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'


class Chat(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, verbose_name='Поездка')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name='Участники')

    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'

    def __str__(self):
        return f'Чат id-{self.pk}'


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE, verbose_name='Чат')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Отправитель')
    content = models.TextField(verbose_name='Сообщение')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    file = models.FileField(upload_to='media/chat_files/', blank=True, null=True, verbose_name='Файл')

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'

    def __str__(self):
        return self.content


class TopicSupport(models.Model):
    name = models.CharField(null=False, verbose_name='Тема')
    count = models.IntegerField(default=0, verbose_name='Количество')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тема чата с техподдержкой'
        verbose_name_plural = 'Темы чатов с техподдержкой'


class ChatSupport(models.Model):
    topic = models.ForeignKey(TopicSupport, null=False, related_name='chat_support', on_delete=models.CASCADE, verbose_name='Тема')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name='Участники')
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_chats', on_delete=models.CASCADE, verbose_name='Создатель')

    class Meta:
        verbose_name = 'Чат с техподдержкой'
        verbose_name_plural = 'Чаты с техподдержкой'

    def __str__(self):
        return f'Чат техподдержки id-{self.pk}'


class MessageSupport(models.Model):
    support_chat = models.ForeignKey(ChatSupport, related_name='message_support', on_delete=models.CASCADE, verbose_name='Чат')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Отправитель')
    content = models.TextField(verbose_name='Сообщение')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    file = models.FileField(upload_to='media/support_chat_files/', blank=True, null=True, verbose_name='Файл')

    class Meta:
        verbose_name = 'Сообщение чата техподдержки'
        verbose_name_plural = 'Сообщения чата техподдержки'

    def __str__(self):
        return self.content


class Feedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, verbose_name='Пользователь')
    content = models.CharField(max_length=255, verbose_name='Отзыв')
    answer = models.CharField(max_length=255, verbose_name='Ответ', null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={
        'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return self.content

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'

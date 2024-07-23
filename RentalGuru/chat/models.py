from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db import models

from RentalGuru import settings


class RequestRent(models.Model):
    STATUS_CHOICES = (
        ('accept', 'Принять'),
        ('denied', 'Отказать'),
        ('unknown', 'Не рассмотренно')
    )
    status = models.CharField(max_length=7, default='unknown', choices=STATUS_CHOICES)
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='request_rent_organized_trips')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')})
    object_id = models.PositiveIntegerField()
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_date = models.DateField()
    end_date = models.DateField()

    @property
    def owner(self):
        return self.vehicle.owner

    def __str__(self):
        return f'request rent id-{self.pk}'


class Trip(models.Model):
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trip_organized_trips')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')})
    object_id = models.PositiveIntegerField()
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_date = models.DateField()
    end_date = models.DateField()

    @property
    def owner(self):
        return self.vehicle.owner

    def __str__(self):
        return f'Trip id-{self.pk}'


class Chat(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL)


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='media/chat_files/', blank=True, null=True)


class TopicSupport(models.Model):
    name = models.CharField(null=False)
    count = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class ChatSupport(models.Model):
    topic = models.ForeignKey(TopicSupport, null=False, related_name='chat_support', on_delete=models.CASCADE)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='created_chats', on_delete=models.CASCADE)


class MessageSupport(models.Model):
    support_chat = models.ForeignKey(ChatSupport, related_name='message_support', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='media/support_chat_files/', blank=True, null=True)
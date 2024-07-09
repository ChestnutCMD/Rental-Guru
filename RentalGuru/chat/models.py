from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from RentalGuru import settings


class Trip(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    vehicle = GenericForeignKey('content_type', 'object_id')

    renter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='trips', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()


class Chat(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL)


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

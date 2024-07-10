from django.db import models

from RentalGuru import settings
from vehicle.models import Vehicle


class Trip(models.Model):
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organized_trips')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='trips')
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

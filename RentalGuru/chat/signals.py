from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Trip, Chat


@receiver(post_save, sender=Trip)
def create_chat_for_trip(sender, instance, created, **kwargs):
    if created:
        chat = Chat.objects.create(trip=instance)
        chat.participants.add(instance.organizer)
        chat.participants.add(instance.vehicle.owner)
        chat.save()

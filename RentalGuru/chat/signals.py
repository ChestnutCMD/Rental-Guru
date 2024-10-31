from django.db.models.signals import post_save
from django.dispatch import receiver

from chat.models import RequestRent, Trip


@receiver(post_save, sender=RequestRent)
def handle_request_rent_post_save(sender, instance, created, **kwargs):
    """Обработчик для создания чата и связанных записей поездок."""
    if created and instance.vehicle:
        # Создаем чат, если заявка доступна "по запросу" и статус "не рассмотрено"
        if instance.vehicle.availabilities.filter(on_request=True).exists() and instance.status == 'unknown':
            instance.create_chat()

    # Если заявка подтверждена, создаем поездку
    if instance.status == 'accept':
        Trip.objects.create(
            organizer=instance.organizer,
            content_type=instance.content_type,
            object_id=instance.object_id,
            start_date=instance.start_date,
            end_date=instance.end_date,
            start_time=instance.start_time,
            end_time=instance.end_time,
            total_cost=instance.total_cost
        )
        
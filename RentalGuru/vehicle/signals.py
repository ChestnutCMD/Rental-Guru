from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from vehicle.models import VehicleBrand, VehicleModel


@receiver(post_save, sender=VehicleBrand)
def update_brand_search_vector(sender, instance, **kwargs):
    VehicleBrand.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('name', config='russian')
    )


@receiver(post_save, sender=VehicleModel)
def update_model_search_vector(sender, instance, **kwargs):
    VehicleModel.objects.filter(pk=instance.pk).update(
        search_vector=SearchVector('name', 'brand__name', config='russian')
    )

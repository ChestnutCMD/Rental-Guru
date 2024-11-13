from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.postgres.search import SearchVector
from transliterate import translit

from vehicle.models import VehicleBrand, VehicleModel


# @receiver(post_save, sender=VehicleBrand)
# def update_brand_search_vector(sender, instance, **kwargs):
#     name_translit = translit(instance.name, language_code='ru')
#
#     instance.search_vector = (
#             SearchVector(models.Value(instance.name), config='english') +
#             SearchVector(models.Value(name_translit), config='russian')
#     )
#     instance.save(update_fields=['search_vector'])
#
#
# @receiver(post_save, sender=VehicleModel)
# def update_model_search_vector(sender, instance, **kwargs):
#     model_name_translit = translit(instance.name, language_code='ru')
#     brand_name_translit = translit(instance.brand.name, language_code='ru')
#
#     instance.search_vector = (
#             SearchVector(models.Value(instance.name), config='english') +
#             SearchVector(models.Value(instance.brand.name), config='english') +
#             SearchVector(models.Value(model_name_translit), config='russian') +
#             SearchVector(models.Value(brand_name_translit), config='russian')
#     )
#     instance.save(update_fields=['search_vector'])

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

from django.core.management.base import BaseCommand
from django.contrib.postgres.search import SearchVector
from django.db import models
from vehicle.models import VehicleBrand, VehicleModel


class Command(BaseCommand):
    help = 'Updates search vectors for vehicle brands and models'

    def handle(self, *args, **kwargs):
        self.stdout.write('Updating search vectors...')

        # # Обновляем вектора поиска для брендов
        # brand_count = VehicleBrand.objects.update(
        #     search_vector=SearchVector('name', config='russian')
        # )
        # self.stdout.write(f'Updated {brand_count} brands')
        #
        # # Обновляем вектора поиска для моделей
        # # Вариант 1: Используя подзапрос
        # model_count = VehicleModel.objects.annotate(
        #     combined_text=Concat(
        #         'name',
        #         models.Value(' '),
        #         'brand__name',
        #         output_field=models.CharField()
        #     )
        # ).update(
        #     search_vector=SearchVector('combined_text', config='russian')
        # )

        # Вариант 2: Через цикл (медленнее, но проще)

        for model in VehicleModel.objects.select_related('brand').iterator():
            combined_text = f"{model.name} {model.brand.name}"
            VehicleModel.objects.filter(pk=model.pk).update(
                search_vector=SearchVector(
                    models.Value(combined_text),
                    config='russian'
                )
            )
        model_count = VehicleModel.objects.count()


        self.stdout.write(f'Updated {model_count} models')
        self.stdout.write(self.style.SUCCESS('Successfully updated all search vectors'))
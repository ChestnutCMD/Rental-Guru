from django.db import models


class RentPriceManager(models.Manager):
    def bulk_create(self, objs, *args, **kwargs):
        for obj in objs:
            commission = (
                obj.vehicle.owner.lessor.commission
                if obj.vehicle.owner and hasattr(obj.vehicle.owner, 'lessor')
                else 10.0
            )
            obj.total = (
                    (float(obj.price) + (float(obj.price) * float(commission) / 100)) *
                    (100 - float(obj.discount)) / 100
            )
        return super().bulk_create(objs, *args, **kwargs)

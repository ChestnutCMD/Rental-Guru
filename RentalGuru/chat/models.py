import json

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from RentalGuru import settings


class RequestRent(models.Model):
    """ Заявки на аренду """
    STATUS_CHOICES = (
        ('accept', 'Принять'),
        ('denied', 'Отказать'),
        ('unknown', 'Не рассмотрено')
    )
    status = models.CharField(max_length=8, default='unknown', choices=STATUS_CHOICES, verbose_name='Статус')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='request_rent_organized_trips', verbose_name='Арендатор')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={
        'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_time = models.TimeField(null=True, blank=True, verbose_name='Время начала аренды')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Время окончания аренды')
    start_date = models.DateField(verbose_name='Начало аренды', null=True, blank=True)
    end_date = models.DateField(verbose_name='Конец аренды', null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Итоговая стоимость', default=0.00)
    deposit_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Залог', default=0.00)
    delivery_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Стоимость доставки')
    delivery = models.BooleanField(default=False, verbose_name='Доставка')
    on_request = models.BooleanField(null=True, blank=True, verbose_name='Заявка по запросу')
    is_deleted = models.BooleanField(default=False, verbose_name='Удалена')

    @property
    def owner(self):
        return self.vehicle.owner

    @property
    def rental_days(self):
        """Подсчитывает количество дней аренды."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    def create_chat(self):
        """Создание чата при подаче заявки или подтверждении аренды."""
        if not Chat.objects.filter(request_rent=self).exists():
            chat = Chat.objects.create(request_rent=self)
            chat.participants.add(self.organizer, self.vehicle.owner)
            chat.save()

            message_content = json.dumps({
                "status": self.status,
                "organizer_id": self.organizer.id,
                "vehicle_id": self.object_id,
                "vehicle_type": str(self.content_type),
                "start_date": str(self.start_date),
                "end_date": str(self.end_date),
                "start_time": str(self.start_time),
                "end_time": str(self.end_time),
                "total_cost": float(self.total_cost),
                "deposit_cost": float(self.deposit_cost),
                "delivery_cost": float(self.delivery_cost),
                "delivery": self.delivery
            }, ensure_ascii=False)

            Message.objects.create(
                chat=chat,
                sender=self.organizer,
                content=message_content
            )

    def calculate_rent_price(self):
        """Подсчитывает итоговую стоимость аренды с fallback на меньший период."""
        from vehicle.models import RentPrice
        rental_days = self.rental_days

        period_priorities = []

        if self.rental_days > 365:
            period_priorities.append(('year', 365))
        if self.rental_days > 30:
            period_priorities.append(('month', 30))
        if self.rental_days > 7:
            period_priorities.append(('week', 7))
        period_priorities.append(('day', 1))

        for period, period_days in period_priorities:
            rent_price = RentPrice.objects.filter(vehicle=self.vehicle, name=period).first()
            if rent_price:
                break
        else:
            raise ValueError("Не найдено подходящей цены аренды для транспортного средства.")

        if self.delivery:
            total_cost = ((rental_days / period_days) * float(rent_price.total)) + float(self.vehicle.price_delivery)
        else:
            total_cost = (rental_days / period_days) * float(rent_price.total)
        return total_cost

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.vehicle and not self.deposit_cost:
                self.deposit_cost = self.vehicle.price_deposit
            self.delivery_cost = self.vehicle.price_delivery if self.delivery else 0.00
            # Рассчитываем итоговую стоимость при создании
            self.total_cost = self.calculate_rent_price()
            # Проверка является ли заявки по запросу
            from vehicle.models import Availability
            availabilities = Availability.objects.filter(vehicle=self.vehicle)
            for availability in availabilities:
                if availability.on_request:
                    self.on_request = True
                    break
                else:
                    self.on_request = False

        else:
            original = RequestRent.objects.get(pk=self.pk)
            if original.status != 'accept' and self.status == 'accept':
                self.total_cost = self.calculate_rent_price()

        super(RequestRent, self).save(*args, **kwargs)

    def __str__(self):
        return f'request rent id-{self.pk}'

    class Meta:
        verbose_name = 'Заявка на аренду'
        verbose_name_plural = 'Заявки на аренду'


class Chat(models.Model):
    request_rent = models.OneToOneField(RequestRent, null=True, on_delete=models.SET_NULL, verbose_name='Заявка на аренду')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name='Участники')

    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'

    def __str__(self):
        return f'chat_id_{self.pk}'


def file_chat_upload_to(instance, filename):
    return f'media/files/chat/{instance.chat}/{filename}'


class Trip(models.Model):
    """ Поездки """
    STATUS_CHOICES = (
        ('current', 'Текущая поездка'),
        ('started', 'В процессе'),
        ('finished', 'Завершить'),
        ('canceled', 'Отменить')
    )
    status = models.CharField(max_length=8, default='current', choices=STATUS_CHOICES, verbose_name='Статус')
    organizer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  related_name='trip_organized_trips', verbose_name='Арендатор')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, limit_choices_to={
        'model__in': ('auto', 'bike', 'ship', 'helicopter', 'specialtechnic')}, verbose_name='Тип транспорта')
    object_id = models.PositiveIntegerField(verbose_name='id транспорта')
    vehicle = GenericForeignKey('content_type', 'object_id')

    start_time = models.TimeField(null=True, blank=True, verbose_name='Время начала аренды')
    end_time = models.TimeField(null=True, blank=True, verbose_name='Время окончания аренды')

    chat = models.OneToOneField(Chat, on_delete=models.SET_NULL, null=True, blank=True)

    start_date = models.DateField(verbose_name='Начало поездки')
    end_date = models.DateField(verbose_name='Конец поездки')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стоимость аренды', default=0.00)

    @property
    def owner(self):
        return self.vehicle.owner

    def save(self, *args, **kwargs):
        if self.pk:
            previous_trip = Trip.objects.get(pk=self.pk)
        else:
            previous_trip = None

        super(Trip, self).save(*args, **kwargs)

        if previous_trip and previous_trip.status != 'finished' and self.status == 'finished':
            self.vehicle.count_trip += 1
            self.vehicle.save(update_fields=['count_trip'])
            self.owner.lessor.count_trip += 1
            self.owner.lessor.save(update_fields=['count_trip'])

    def __str__(self):
        return f'Поездка id-{self.pk}'

    class Meta:
        verbose_name = 'Поездка'
        verbose_name_plural = 'Поездки'


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE, verbose_name='Чат')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Отправитель')
    content = models.TextField(verbose_name='Сообщение')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    file = models.FileField(upload_to=file_chat_upload_to, blank=True, null=True, verbose_name='Файл')
    deleted = models.BooleanField(default=False, verbose_name='Удалено')

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
        ordering = ['-count']


class ChatSupport(models.Model):
    creator = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='created_chats', on_delete=models.CASCADE,
                                   verbose_name='Создатель')

    class Meta:
        verbose_name = 'Чат с техподдержкой'
        verbose_name_plural = 'Чаты с техподдержкой'

    def __str__(self):
        return f'support_chat_id_{self.pk}'


class IssueSupport(models.Model):
    chat = models.ForeignKey(ChatSupport, null=False, on_delete=models.CASCADE, related_name='issue_chat',
                             verbose_name='Чат техподдержки')
    topic = models.ForeignKey(TopicSupport, null=False, related_name='chat_support', on_delete=models.CASCADE,
                              verbose_name='Тема')
    description = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')

    class Meta:
        verbose_name = 'Обращение в техподдержку'
        verbose_name_plural = 'Обращения в техподдержку'

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            from .tasks import send_issue_email
            send_issue_email.delay(self.id)


def file_support_chat_upload_to(instance, filename):
    return f'media/files/chat_support/{instance.chat}/{filename}'


class MessageSupport(models.Model):
    chat = models.ForeignKey(ChatSupport, related_name='message_support', on_delete=models.CASCADE, verbose_name='Чат')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Отправитель')
    content = models.TextField(verbose_name='Сообщение')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    file = models.FileField(upload_to=file_support_chat_upload_to, blank=True, null=True, verbose_name='Файл')
    deleted = models.BooleanField(default=False, verbose_name='Удалено')

    class Meta:
        verbose_name = 'Сообщение чата техподдержки'
        verbose_name_plural = 'Сообщения чата техподдержки'

    def __str__(self):
        return self.content

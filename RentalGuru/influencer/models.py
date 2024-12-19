import string
import random
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.utils.timezone import now

from RentalGuru import settings


class RegistrationSource(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registration_source', verbose_name='Пользователь')
    influencer = models.ForeignKey('Influencer', on_delete=models.CASCADE, related_name='registrations', verbose_name='Инфлюенсер')
    source_type = models.CharField(max_length=20, choices=[('referral', 'Реферальная ссылка'), ('qr_code', 'QR-код'), ('promo', 'Промокод')], verbose_name='Тип источника')
    source_details = models.CharField(max_length=100, blank=True, verbose_name='Детали источника (ссылка, qr код и т.д.)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата регистрации')


class Influencer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='influencer', verbose_name='Пользователь')
    referral_code = models.CharField(max_length=20, unique=True, verbose_name='Реферальный код')
    organization = models.OneToOneField('Organization', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Организация')
    commission = models.PositiveIntegerField(default=5, null=True, blank=True)

    def __str__(self):
        return f'{self.user.first_name} - {self.referral_code}'

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_unique_referral_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_referral_code():
        while True:
            length = 8
            chars = string.ascii_uppercase + string.digits
            code = ''.join(random.choice(chars) for _ in range(length))
            if not Influencer.objects.filter(referral_code=code).exists():
                return code

    class Meta:
        verbose_name = 'Инфлюенсер'
        verbose_name_plural = 'Инфлюенсеры'


def upload_renter_document(instance, filename):
    return f'media/images/users/{instance.influencer.user.id}/documents/{filename}'


class InfluencerDocuments(models.Model):
    STATUS_CHOICES = (
        ('pending', 'На проверке'),
        ('approved', 'Подтверждено'),
        ('rejected', 'Отклонено'),
    )

    influencer = models.OneToOneField(Influencer, on_delete=models.CASCADE, verbose_name='Партнер', related_name='document')
    number = models.CharField(verbose_name='Серия и номер')
    photo = models.ImageField(upload_to=upload_renter_document, verbose_name='Фото')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name='Статус проверки')

    def __str__(self):
        return f'Паспорт: {self.number}'

    class Meta:
        verbose_name = 'Паспортные данные'
        verbose_name_plural = 'Паспортные данные'


class Organization(models.Model):
    name = models.CharField(max_length=255, verbose_name="Название организации")
    country = models.CharField(max_length=100, verbose_name="Страна")
    city = models.CharField(max_length=100, verbose_name="Город")
    address = models.CharField(max_length=255, verbose_name="Адрес")
    contacts = models.ManyToManyField('Contact', verbose_name="Контакты", blank=True)
    bank_details = models.OneToOneField(
        'BankDetails',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Банковские реквизиты"
    )

    def __str__(self):
        return self.name


class Contact(models.Model):
    CONTACT_TYPE_CHOICES = [('phone', 'Телефон'), ('email', 'Эл.почта'),]
    contact_type = models.CharField(max_length=10, choices=CONTACT_TYPE_CHOICES, verbose_name="Тип контакта")
    value = models.CharField(max_length=100, verbose_name="Значение")
    is_primary = models.BooleanField(default=False, verbose_name="Основной контакт")

    def __str__(self):
        return f"{CONTACT_TYPE_CHOICES_DICT.get(str(self.contact_type), self.contact_type)}: {self.value}"


CONTACT_TYPE_CHOICES_DICT = dict(Contact.CONTACT_TYPE_CHOICES)


class BankDetails(models.Model):
    inn = models.CharField(max_length=12, verbose_name="ИНН")
    ogrn = models.CharField(max_length=15, verbose_name="ОГРН")
    registration_date = models.DateField(verbose_name="Дата регистрации")
    account_number = models.CharField(max_length=20, verbose_name="Расчетный счет")
    account_owner = models.CharField(max_length=255, verbose_name="ФИО владельца счета")

    def __str__(self):
        return f"ИНН: {self.inn}, Счет: {self.account_number}"


class ReferralLink(models.Model):
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name='referral_links', verbose_name='Инфлюенсер')
    channel = models.CharField(max_length=50, verbose_name='Название канала')
    link = models.URLField(blank=True, verbose_name='Ссылка')
    count = models.PositiveIntegerField(default=0, verbose_name='Количество регистраций')

    def __str__(self):
        return f'{self.influencer.user.first_name} - {self.channel}'

    def save(self, *args, **kwargs):
        if not self.link:
            self.link = self.generate_referral_link()
        super().save(*args, **kwargs)

    def generate_referral_link(self):
        base_url = f"{settings.HOST_URL}/app/users/"
        random_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        return f"{base_url}?ref={self.influencer.referral_code}&code={random_code}"

    class Meta:
        verbose_name = 'Реферальная ссылка'
        verbose_name_plural = 'Реферальные ссылки'


class InfluencerRequest(models.Model):
    name = models.CharField(max_length=50, verbose_name='Имя')
    city = models.CharField(max_length=50, verbose_name='Город', null=True, blank=True)
    telephone = models.CharField(max_length=15, null=True, blank=True, verbose_name='Телефон')
    email = models.EmailField(verbose_name='Email')
    social = models.CharField(max_length=250, verbose_name='Сайт или соцсеть')
    description = models.CharField(max_length=250, verbose_name='Чем вы занимаетесь')
    created_at = models.DateField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Заявка на создание инфлюенсера'
        verbose_name_plural = 'Заявки на создание инфлюенсеров'


def qr_code_upload_path(instance, filename):
    """Функция для генерации пути сохранения QR-кодов."""
    return f'media/images/users/{instance.influencer.user.id}/{filename}'


class QRCode(models.Model):
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name='qr_codes', verbose_name='Инфлюенсер')
    channel = models.CharField(max_length=100, verbose_name='Название канала')
    referral_link = models.URLField(blank=True, verbose_name='Реферальная ссылка')
    qr_code_image = models.ImageField(upload_to=qr_code_upload_path, blank=True, verbose_name='QR-код')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    count = models.PositiveIntegerField(default=0, verbose_name='Количество регистраций')

    def save(self, *args, **kwargs):
        if not self.referral_link:
            self.referral_link = self.generate_referral_link()

        self.qr_code_image = self.generate_qr_code()

        super().save(*args, **kwargs)

    def generate_referral_link(self):
        """Генерация реферальной ссылки на основе канала и инфлюенсера."""
        base_url = getattr(settings, "HOST_URL", "http://localhost:8000") + "/app/users/"
        query_params = {
            "ref": self.influencer.referral_code,
            "code": ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        }
        return f"{base_url}?{urlencode(query_params)}"

    def generate_qr_code(self):
        """Генерация QR-кода и сохранение его в поле qr_code_image."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.referral_link)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        file_name = f"qr_{self.influencer.user.id}_{self.channel}.png"

        return ContentFile(buffer.read(), name=file_name)

    class Meta:
        verbose_name = 'QR-код'
        verbose_name_plural = 'QR-коды'


class PromoCode(models.Model):
    title = models.CharField(max_length=50, unique=True, verbose_name='Заголовок')
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Партнер')
    percent = models.BooleanField(verbose_name='Процент')
    cash = models.BooleanField(verbose_name='Бонусные рубли')
    total = models.PositiveIntegerField(verbose_name='Колличество')
    expiration_date = models.DateTimeField(verbose_name='Срок действия', null=True, blank=True)
    count = models.PositiveIntegerField(default=0, verbose_name='Количество регистраций')

    class Meta:
        verbose_name = 'Промокод'
        verbose_name_plural = 'Промокоды'

    def __str__(self):
        if self.percent:
            promo = 'процент'
        else:
            promo = 'бонусные рубли'
        return f'Промокод {self.title}: {self.total} {promo}'

    def clean(self):
        if not (self.percent or self.cash):
            raise ValidationError('Должно быть выбрано хотя бы одно из полей: "Процент" или "Бонусные рубли".')

        if self.percent and self.cash:
            raise ValidationError('Поля "Процент" и "Бонусные рубли" не могут быть выбраны одновременно.')

        if self.percent and int(self.total) > 50:
            raise ValidationError('Если "Процент" выбран, "Количество" не может превышать 50.')

        if self.expiration_date and self.expiration_date < now():
            raise ValidationError('Срок действия промокода не может быть в прошлом.')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def is_active(self):
        """
        Проверяет, активен ли промокод в текущий момент.
        """
        if self.expiration_date:
            return now() <= self.expiration_date
        return True

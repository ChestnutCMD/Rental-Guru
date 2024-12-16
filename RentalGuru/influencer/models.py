import string
import random
from io import BytesIO
from urllib.parse import urlencode

import qrcode
from django.core.files.base import ContentFile
from django.db import models
from RentalGuru import settings
from franchise.models import City


class Influencer(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    referral_code = models.CharField(max_length=20, unique=True, verbose_name='Реферальный код')

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
    return f'qr_codes/{instance.influencer.user.id}/{filename}'


class QRCode(models.Model):
    influencer = models.ForeignKey(Influencer, on_delete=models.CASCADE, related_name='qr_codes', verbose_name='Инфлюенсер')
    channel = models.CharField(max_length=100, verbose_name='Название канала')
    referral_link = models.URLField(blank=True, verbose_name='Реферальная ссылка')
    qr_code_image = models.ImageField(upload_to=qr_code_upload_path, blank=True, verbose_name='QR-код')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

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

import string
import random
from django.db import models
from RentalGuru import settings


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
    influencer = models.ForeignKey('Influencer', on_delete=models.CASCADE, related_name='referral_links', verbose_name='Инфлюенсер')
    channel = models.CharField(max_length=50, verbose_name='Название канала')  # YouTube, Telegram, Instagram, etc.
    link = models.URLField(blank=True, verbose_name='Ссылка')
    count = models.PositiveIntegerField(default=0, verbose_name='Количество регистраций')

    def __str__(self):
        return f'{self.influencer.user.first_name} - {self.channel}'

    def save(self, *args, **kwargs):
        if not self.link:
            self.link = self.generate_referral_link()
        super().save(*args, **kwargs)

    def generate_referral_link(self):
        base_url = f"{settings.HOST_URL}/app/users/"  # Замените на фактический базовый URL вашего сайта
        random_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        return f"{base_url}?ref={self.influencer.referral_code}&code={random_code}"

    class Meta:
        verbose_name = 'Реферальная ссылка'
        verbose_name_plural = 'Реферальные ссылки'

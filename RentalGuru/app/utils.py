from typing import Union, Dict, Any
from django.db.models import Model

from app.models import User
from influencer.models import ReferralLink, QRCode, PromoCode, UsedPromoCode


def increment_count(obj: Model) -> None:
    """Увеличивает счётчик и сохраняет объект."""
    obj.count += 1
    obj.save()


def referal_check(user: User, ref: str = None, code: str = None, promocode: str = None) -> Union[bool, Dict[str, Any]]:
    if ref and code:
        # Проверяем реферальную ссылку
        referral_link = ReferralLink.objects.filter(influencer__referral_code=ref, link__icontains=code).first()
        if referral_link:
            increment_count(referral_link)
            user.influencer = referral_link.influencer
            user.save()
        else:
            qr_code = QRCode.objects.filter(influencer__referral_code=ref, referral_link__icontains=code).first()
            if qr_code:
                increment_count(qr_code)
                user.influencer = qr_code.influencer
                user.save()
            else:
                return {"referral_code": "Неправильный реферальный код или ссылка."}
    elif promocode:
        # Проверяем промокод
        promo = PromoCode.objects.filter(title=promocode).first()
        if not promo:
            return {"referral_code": "Неправильный промокод"}

        increment_count(promo)

        if promo.type == 'cash' and hasattr(user, 'renter'):
            # Добавляем бонусы пользователю
            renter = user.renter
            renter.bonus_account = promo.total
            renter.save()
            # Отмечаем использование промокода
            UsedPromoCode.objects.create(user=user, promo_code=promo, used=True)
        else:
            UsedPromoCode.objects.create(user=user, promo_code=promo)
        # Привязываем инфлюенсера, если есть
        if promo.influencer:
            user.influencer = promo.influencer
            user.save()

    return True

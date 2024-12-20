from django.utils.timezone import now

from influencer.models import PromoCode, UsedPromoCode


def check_promocode(user, promocode):
    """
    Проверка промокода при отправке заявки
    :param user:
    :param promocode:
    :return:
    """
    # Пользователь является арендатором
    if not hasattr(user, 'renter'):
        return False
    # Поиск промокода
    try:
        promo_code = PromoCode.objects.get(title=promocode)
    except PromoCode.DoesNotExist:
        return False
    # Проверка срока действия промокода
    if promo_code.expiration_date and promo_code.expiration_date < now():
        return False
    # Промокод использован
    if UsedPromoCode.objects.filter(user=user, promo_code=promo_code, used=True).exists():
        return False
    # Промокод не применен
    if not UsedPromoCode.objects.filter(user=user, promo_code=promo_code, used=False).exists():
        return "Промокод не применен. Нажмите на кнопку применить"

    return True

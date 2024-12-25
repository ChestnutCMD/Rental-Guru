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
        return "Промокод недействителен. Вы не являетесь арендатором."

    # Поиск промокода
    try:
        promo_code = PromoCode.objects.get(title=promocode)
    except PromoCode.DoesNotExist:
        return "Промокод не найден."

    # Проверка срока действия промокода
    if promo_code.expiration_date and promo_code.expiration_date < now():
        return "Срок действия промокода истек."

    # Промокод использован
    if UsedPromoCode.objects.filter(user=user, promo_code=promo_code, used=True).exists():
        return "Промокод уже использован."

    # Промокод не применен
    if not UsedPromoCode.objects.filter(user=user, promo_code=promo_code, used=False).exists():
        return "Промокод не применен. Нажмите на кнопку применить."

    return promo_code

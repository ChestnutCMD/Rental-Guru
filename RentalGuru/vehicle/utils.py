from datetime import timedelta


def merge_periods(periods):
    """ Преобразуем даты из объектов datetime в строки и сортируем периоды по начальной дате """
    if not periods:
        return []

    # Преобразуем даты в строки и сортируем периоды
    periods = sorted(periods, key=lambda x: x['start_date'])

    # Фильтруем периоды с некорректными датами
    valid_periods = [p for p in periods if p['start_date'] <= p['end_date']]

    if not valid_periods:
        return []

    merged_periods = []
    current_period = valid_periods[0]

    for i in range(1, len(valid_periods)):
        start_current = current_period['start_date']
        end_current = current_period['end_date']

        start_next = valid_periods[i]['start_date']
        end_next = valid_periods[i]['end_date']

        # Если текущий период перекрывается или смежен с следующим
        if end_current >= start_next - timedelta(days=1):
            # Обновляем конец текущего периода, если конец следующего периода больше
            current_period['end_date'] = max(end_current, end_next)
        else:
            # Добавляем текущий период в результат и начинаем новый период
            merged_periods.append(current_period)
            current_period = valid_periods[i]

    merged_periods.append(current_period)

    return merged_periods


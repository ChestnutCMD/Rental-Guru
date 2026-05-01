# 🚗 Rental Guru

> **B2B-платформа для аренды транспорта премиум-класса и спецтехники**  
> Автомобили, мотоциклы, катера, вертолёты, спецтехника — полный цикл аренды с realtime-коммуникацией

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14-red?logo=django)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0-orange?logo=redis)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-24.0-blue?logo=docker)](https://www.docker.com/)

---

## 📋 О проекте

**Rental Guru** — это backend-платформа для сервиса аренды транспорта, построенная на **Django REST Framework**. Проект решает комплексные бизнес-задачи: от поиска и бронирования до realtime-чатов между арендаторами и владельцами, онлайн-платежей и гибкой системы партнёрств.

### 🎯 Ключевая особенность

Платформа поддерживает **любые типы транспорта** через полиморфную архитектуру, что позволяет легко масштабировать систему и добавлять новые категории без изменения базовой логики.

---

## ✨ Основные возможности

### 👥 Пользователи и роли

| Роль | Возможности |
|------|-------------|
| **Member** | Аренда, чаты, отзывы, избранное |
| **Manager** | Модерация транспорта, управление пользователями |
| **Administrator** | Полный доступ ко всем разделам |

**Аутентификация:**
- JWT с обновлением токенов
- Telegram Login Widget (с проверкой hash)
- OAuth 2.0: VK, Yandex, Mail.ru
- Автоматическое связывание с партнёрскими кодами

### 🚤 Транспорт (полиморфная архитектура)

Все модели наследуются от базового `Vehicle`:

```python
class Vehicle(models.Model):
    brand = models.ForeignKey(VehicleBrand)
    model = models.ForeignKey(VehicleModel)
    price_per_day = models.DecimalField()
    # ... общие поля

class Auto(Vehicle):
    engine_power = models.IntegerField()
    transmission = models.CharField()
    fuel_type = models.CharField()

class Boat(Vehicle):
    length = models.DecimalField()
    cabin_count = models.IntegerField()

class Helicopter(Vehicle):
    max_altitude = models.IntegerField()
    engine_count = models.IntegerField()

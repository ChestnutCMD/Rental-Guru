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
```

‎**Поддерживаемые типы:**
* Автомобили
* Мотоциклы
* ‎Катера и яхты
* ‎Вертолёты
* ‎Спецтехника
‎
### 🔍 Полнотекстовый поиск
‎
‎**Реализован на PostgreSQL Full Text Search с продвинутыми функциями:**
‎
* Триграммы (pg_trgm) для нечёткого поиска
* Транслитерация (русский ↔ английский)
* Автодополнение при частичном вводе
* Обновление индексов через Celery + сигналы Django
‎
```python
‎# Пример поиска
‎"Honda" → все автомобили Honda
‎"Hond"  → автодополнение до "Honda"
‎"Хонда" → транслитерация, поиск "Honda"
```
### 💬 Чат с realtime-возможностями
‎
‎**WebSocket через Django Channels:**

* Отправка сообщений с файлами
* Уведомление о прочтении
* Возможность изменять условия аренды прямо в чате
* Автоматический перевод сообщений (см. раздел "Мультиязычность")
‎
### 🌐 Мультиязычность и переводы
‎
‎**Система мультиязычности интерфейса:**

* Middleware для определения языка пользователя
* Кэширование переводов для высокой производительности
* Поддержка динамического переключения языков
‎
### 🤖 Автоматический realtime-перевод сообщений в чатах
‎
* Входящие сообщения переводятся на язык пользователя
* Пользователи могут общаться на разных языках
* Перевод происходит автоматически через интеграцию с переводческим API
* Поддерживается кэширование переводов для оптимизации
‎
```python
‎# Пример работы чата
‎Арендатор (ru): "Когда могу забрать авто?"
‎Владелец (en): "When can I pick up the car?"  # автоматический перевод
```
‎
### 🔐 Гибкая система прав доступа менеджеров
‎**Реализована расширенная система permissions:**
```python
‎class ManagerPermissions(BasePermission):
‎    """
‎    Гибкое разграничение прав для менеджеров:
‎    - Доступ к определённым разделам
‎    - Ограничение действий по ролям
‎    - Модерация транспорта
‎    - Управление пользователями
‎    """
‎    def has_permission(self, request, view):
‎        if not request.user.is_authenticated:
‎            return False
‎        if request.user.role == 'administrator':
‎            return True
‎        if request.user.role == 'manager':
‎            # Проверка доступа к конкретному разделу
‎            return view.action in request.user.manager_permissions
‎        return False
‎
‎class IsVehicleModerator(BasePermission):
‎    """Может модерировать только свой тип транспорта"""
‎    def has_permission(self, request, view):
‎        if not request.user.is_authenticated:
‎            return False
‎        return request.user.can_moderate_vehicle_type(view.vehicle_type)
```
**‎Возможности:**
* Назначение прав на конкретные разделы
* Ограничение действий (только чтение / редактирование)
* Модерация транспорта с разной степенью доступа
‎
### 💳 Онлайн-платежи (Тинькофф API)
* Создание платежей и проверка статуса
* Обработка webhook от банка
* Поддержка полной и частичной оплаты
* Возврат средств (рефанды)
```python
‎# Пример интеграции с Тинькофф
‎class TinkoffPaymentService:
‎    def create_payment(self, amount, order_id, description):
‎        payload = {
‎            'Amount': amount * 100,  # в копейках
‎            'OrderId': order_id,
‎            'Description': description,
‎            'Language': 'ru'
‎        }
‎        return self._request('Init', payload)
‎
‎    def check_payment(self, payment_id):
‎        return self._request('GetState', {'PaymentId': payment_id})
```
### 📅 Календарь бронирований
* Визуальный выбор дат аренды
* Блокировка занятых дат
* Поддержка режима "аренда по запросу"
* Realtime-обновление доступности

### 🌟 Система рейтингов и отзывов
* Рейтинг транспорта (средняя оценка)
* Рейтинг арендаторов (как надёжность)
* Отзывы с оценками (1-5 звёзд)
* Связь отзывов с конкретными арендами
‎
### 👥 Партнёрская система и франшиза
* Промокоды на скидку
* Реферальная программа (возврат бонусов)
* Система франшиз (для региональных партнёров)
* Бонусные механики (кешбэк за привлечённых клиентов)
‎
### 📄 Документы арендаторов
* Безопасное хранение документов (паспорт, права)
* Разграничение доступа (только владелец и администратор)
* Поддержка скан-копий и фотографий
* Автоматическая проверка срока действия

### 💾 Загрузка файлов

‎**Структурированное хранение:**

```
‎media/
‎├── files/
‎│   └── chat/
‎│       └── {chat_id}/
‎│           └── {timestamp}_{filename}
‎├── vehicles/
‎│   └── {vehicle_id}/
‎│       └── photos/
‎│           └── {uuid}.jpg
‎├── documents/
‎│   └── {user_id}/
‎│       └── {document_type}/
‎│           └── {filename}
```
‎
### 🔔 Уведомления
‎**Мультиканальная система:**
* Push уведомления (через Firebase🔥)
* Email уведомления (HTML-шаблоны)
* SMS уведомления (через шлюз)
* Realtime-обновления статуса заявок
* Уведомления о новых сообщениях в чатах
* Фоновая обработка через Celery

---
### 🛠 Технологический стек

* ‎**Backend:** Python 3.11, Django 4.2, DRF 3.14
* **‎Database:** PostgreSQL 15 (PostGIS, pg_trgm, tsvector)
* **Cache & Broker:** Redis 7.0
* **Async Tasks:** Celery 5.3
* **Realtime:** Django Channels 4.0 + WebSocket
* **‎Auth:** JWT, allauth (Telegram, VK, Yandex, Mail.ru)
* **‎API Docs:** drf-spectacular (OpenAPI/Swagger)
* **‎Payments:** Tinkoff API
* **‎Translation:** Google Translate API + cache
* **‎Deployment:** Docker, Docker Compose, Nginx, GitHub actions

---

### 🚀 Быстрый старт
‎Локальный запуск

```bash
# 1. Клонирование
‎git clone https://github.com/ChestnutCMD/Rental-Guru.git
‎cd Rental-Guru
‎
# 2. Виртуальное окружение
‎python -m venv venv
‎source venv/bin/activate  # Linux/macOS
‎# venv\Scripts\activate   # Windows
‎
‎# 3. Установка зависимостей
‎pip install -r requirements/base.txt
‎
‎# 4. Настройка .env
‎cp .env.example .env
‎# Отредактируйте .env под себя (БД, Redis, API ключи)
‎
‎# 5. Миграции
‎python manage.py migrate
‎
‎# 6. Загрузка тестовых данных (опционально)
‎python manage.py loaddata fixtures/demo.json
‎
‎# 7. Запуск сервера
‎python manage.py runserverrunserver
```
‎Docker Compose
```bash
# Запуск всех сервисов
‎docker compose up --build
‎
‎# Фоновый режим
‎docker compose up -d
‎
‎# Остановка
‎docker compose down
‎
‎# Просмотр логов
‎docker compose logs -ff
```

**‎После запуска:**
‎
‎· API: http://localhost:8000
‎· Swagger Docs: http://localhost:8000/api/docs/
‎· Admin: http://localhost:8000/admin
‎· Flower (Celery мониторинг): http://localhost:5555
‎
‎Запуск WebSocket (Django Channels)
```bash
‎# Для разработки (с Channels)
‎python manage.py runserver
‎
‎# Для продакшена через Daphne (ASGI сервер)
‎daphne -b 0.0.0.0 -p 8000 config.asgi:application
```
Celery воркер

```bash
‎# Воркер для фоновых задач
‎celery -A config worker -l info
‎
‎# Beat для периодических задач
‎celery -A config beat -l info
‎
‎# Мониторинг через Flower
‎celery -A config flowerflower

```
---
### 📖 API Документация
‎
* OpenAPI схема: /api/schema/
* Swagger UI: /api/docs/
* ReDoc: /api/redoc/
‎
‎Документация генерируется автоматически через drf-spectacular с подробными описаниями эндпоинтов, схемами запросов/ответов и примерами.

---

### 🔒 Безопасность
‎
* JWT с коротким временем жизни (15 минут) и refresh-токенами (7 дней)
* Кастомные permissions: IsAdminOrOwner, IsAdminOrLessor, IsManagerWithAccess
* Проверка владельца объекта через декораторы
* Защита WebSocket соединений (проверка JWT при handshake)
* CORS настройки для ограничения доменов
* Валидация Telegram hash при авторизации (подпись запроса)
* Rate limiting на API эндпоинтах
* Санитизация пользовательского ввода
‎
```python
‎# Пример WebSocket JWT проверки
‎class JWTAuthMiddleware:
‎    async def __call__(self, scope, receive, send):
‎        token = self.get_token_from_scope(scope)
‎        if token:
‎            user = await self.get_user_from_token(token)
‎            scope['user'] = user
‎        return await super().__call__(scope, receive, send)
```
---
### 📈 Особенности, выделяющие проект
‎‎**1. Полиморфная архитектура транспорта**
‎
‎Позволяет добавлять новые типы транспорта без изменения кода API и базовой логики аренды. Единый эндпоинт для всех типов с автоматической сериализацией специфических полей.

‎**‎2. Продвинутый поиск**

‎Поддержка транслитерации, нечёткого поиска (триграммы) и автодополнения делает пользовательский опыт на уровне крупных маркетплейсов. Поисковые индексы обновляются асинхронно через Celery.
‎
**‎3. Полноценная realtime-архитектура**
‎
* Веб-чаты с обменом файлами и уведомлениями о прочтении
* Обновление статусов аренды без перезагрузки страницы
* Уведомления в реальном времени о событиях

‎**‎4. Мультиязычность с автоматическим переводом чатов**
‎
‎Пользователи на разных языках могут комфортно общаться без языкового барьера. Перевод выполняется асинхронно с кэшированием результатов.

‎**‎5. Гибкая система прав менеджеров**
‎
‎Позволяет делегировать полномочия без предоставления полного административного доступа. Настраивается доступ к конкретным разделам и типам транспорта.
‎
**‎6. Поддержка аренды по запросу**
‎
‎Уникальный режим, когда владелец лично утверждает каждую заявку через чат, с возможностью изменения условий (дата, цена, дополнительные услуги).
‎
‎**7. Полная интеграция с Тинькофф**
‎
‎Приём платежей, холдирование депозитов, автоматические возвраты, обработка webhook с подтверждением.

---
### 🐳 CI/CD
‎
‎Проект настроен на автоматический деплой через GitHub Actions:

```yaml
‎# .github/workflows/deploy.yml
‎name: Deploy to Production
‎
‎on:
‎  push:
‎    branches: [main]
‎
‎jobs:
‎  test:
‎    runs-on: ubuntu-latest
‎    steps:
‎      - uses: actions/checkout@v3
‎      - name: Run tests
‎        run: |
‎          docker compose -f docker-compose.ci.yml run web pytest
‎
‎  deploy:
‎    needs: test
‎    runs-on: ubuntu-latest
‎    steps:
‎      - name: Deploy to VPS
‎        uses: appleboy/ssh-action@v0.1.5
‎        with:
‎          host: ${{ secrets.VPS_HOST }}
‎          username: ${{ secrets.VPS_USER }}
‎          key: ${{ secrets.SSH_KEY }}
‎          script: |
‎            cd /app/Rental-Guru
‎            git pull
‎            docker compose down
‎            docker compose up -d --build-build

```
---

### 📋 Roadmap
‎
‎Реализовано ✅
‎
* Полиморфная архитектура транспорта
* Полнотекстовый поиск с триграммами
* WebSocket чаты с файлами
* JWT + OAuth авторизация (Telegram, VK, Yandex, Mail.ru)
* Онлайн-платежи через Тинькофф API
* Система аренды по запросу
* Мультиязычность и перевод чатов
* Система прав доступа менеджеров

---

### 👨‍💻 Автор
‎
‎Разработчик backend-части
‎
‎GitHub: @ChestnutCMD
‎
‎Проект: Rental-Guru
‎
**‎Стек, с которым работал в проекте:**
‎
* Django / DRF / Django Channels
* PostgreSQL / Redis / Celery
* WebSocket / JWT / OAuth 2.0
* Docker / Nginx / GitHub Actions
* Tinkoff API / Google Translate API

---
### 📄 Лицензия
‎
‎MIT License
‎
‎Copyright (c) 2024-2026 ChestnutCMD
‎
‎Permission is hereby granted, free of charge, to any person obtaining a copy
‎of this software and associated documentation files (the "Software"), to deal
‎in the Software without restriction, including without limitation the rights
‎to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
‎copies of the Software, and to permit persons to whom the Software is
‎furnished to do so, subject to the following conditions...

---

### ⭐️ Проект представлен в рамках портфолио. Весь код написан автором.

‎tg: @dbqp3
email: 13can133@gmail.com

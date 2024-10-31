from datetime import datetime, time, date
from decimal import Decimal
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, permissions, status, serializers, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from RentalGuru import settings
from app.models import User, RenterDocuments
from notification.models import Notification
from payment.models import Transaction, PaymentSetting
from payment.services import TinkoffPaymentService
from vehicle.models import Auto, Bike, Ship, Helicopter, SpecialTechnic, Availability
from .filters import FeedbackFilter, MessageFilter
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, Feedback
from .permissions import IsAdminOrOwner, IsParticipantOrAdmin, IsChatCreatorOrAdmin
from .serializers import TripSerializer, ChatSerializer, MessageSerializer, RequestRentSerializer, \
    TopicSupportSerializer, ChatSupportSerializer, MessageSupportSerializer, FeedbackUpdateSerializer, \
    FeedbackSerializer, FeedbackCreateSerializer
from rest_framework.exceptions import ValidationError as DRFValidationError, PermissionDenied, ValidationError
from .utils import is_period_contained, subtract_periods, calculate_age


@extend_schema(summary="Поездка", description='Поездка')
class TripViewSet(viewsets.ModelViewSet):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        auto_content_type = ContentType.objects.get_for_model(Auto)
        bike_content_type = ContentType.objects.get_for_model(Bike)
        ship_content_type = ContentType.objects.get_for_model(Ship)
        helicopter_content_type = ContentType.objects.get_for_model(Helicopter)
        special_technic_content_type = ContentType.objects.get_for_model(SpecialTechnic)

        return Trip.objects.filter(Q(organizer=user) |
                                   Q(content_type=auto_content_type,
                                     object_id__in=Auto.objects.filter(owner=user).values('id')) |
                                   Q(content_type=bike_content_type,
                                     object_id__in=Bike.objects.filter(owner=user).values('id')) |
                                   Q(content_type=ship_content_type,
                                     object_id__in=Ship.objects.filter(owner=user).values('id')) |
                                   Q(content_type=helicopter_content_type,
                                     object_id__in=Helicopter.objects.filter(owner=user).values('id')) |
                                   Q(content_type=special_technic_content_type,
                                     object_id__in=SpecialTechnic.objects.filter(owner=user).values('id')))

    # @action(detail=True, methods=['post'])
    # def pay_remaining(self, request, pk=None):
    #     trip = self.get_object()
    #     if trip.status != 'current':
    #         return Response({"error": "Оплата возможна только для текущих поездок"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     tinkoff_service = TinkoffPaymentService()
    #     remaining_amount = trip.total_cost * Decimal('0.7')  # 70% от общей стоимости
    #
    #     payment = tinkoff_service.init_payment(
    #         amount=remaining_amount,
    #         order_id=f"trip-{trip.id}",
    #         description=f"Оплата за аренду {trip.vehicle}"
    #     )
    #
    #     if payment.get('Success'):
    #         Transaction.objects.create(
    #             user=request.user,
    #             amount=remaining_amount,
    #             transaction_type='full_payment',
    #             trip=trip,
    #             tinkoff_payment_id=payment['PaymentId'],
    #             status='pending'
    #         )
    #         return Response({"payment_url": payment['PaymentURL']})
    #     else:
    #         return Response({"error": "Не удалось инициировать платеж"}, status=status.HTTP_400_BAD_REQUEST)

    # @action(detail=True, methods=['post'])
    # def confirm_payment(self, request, pk=None):
    #     trip = self.get_object()
    #     transaction = Transaction.objects.filter(trip=trip, transaction_type='full_payment').last()
    #
    #     if not transaction:
    #         return Response({"error": "Транзакция не найдена"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     tinkoff_service = TinkoffPaymentService()
    #     payment_status = tinkoff_service.check_payment_status(transaction.tinkoff_payment_id)
    #
    #     if payment_status.get('Status') == 'CONFIRMED':
    #         transaction.status = 'completed'
    #         transaction.save()
    #         trip.status = 'finished'
    #         trip.save()
    #         self.distribute_funds(trip, transaction.amount)
    #         return Response({"message": "Оплата успешно завершена"})
    #     else:
    #         return Response({"error": "Платеж не подтвержден"}, status=status.HTTP_400_BAD_REQUEST)

    # @staticmethod
    # def distribute_funds(trip, amount):
    #     settings = PaymentSetting.objects.first()
    #     owner = trip.owner
    #
    #     if owner.lessor.franchise:
    #         franchise_amount = amount * (settings.FRANCHISE_COMMISSION_PERCENTAGE / 100)
    #         owner_amount = amount - franchise_amount
    #         platform_amount = franchise_amount * (settings.RENT_COMMISSION_PERCENTAGE / 100)
    #         franchise_amount -= platform_amount
    #     else:
    #         owner_amount = amount
    #         platform_amount = amount * (settings.RENT_COMMISSION_PERCENTAGE / 100)
    #         owner_amount -= platform_amount
    #         franchise_amount = 0
    #
    #     # Создаем транзакции для каждого участника
    #     Transaction.objects.create(
    #         user=owner.user,
    #         amount=owner_amount,
    #         transaction_type='income',
    #         trip=trip,
    #         status='completed'
    #     )
    #
    #     if franchise_amount > 0:
    #         Transaction.objects.create(
    #             user=owner.lessor.franchise.director,
    #             amount=franchise_amount,
    #             transaction_type='franchise_income',
    #             trip=trip,
    #             status='completed'
    #         )
    #
    #     platform_user = User.objects.filter(role='admin').first()
    #     Transaction.objects.create(
    #         user=platform_user,
    #         amount=platform_amount,
    #         transaction_type='platform_income',
    #         trip=trip,
    #         status='completed'
    #     )
    #
    #     # Расчет для инфлюенсера
    #     if trip.organizer.renter.influencer:
    #         influencer_amount = platform_amount * (settings.INFLUENCER_COMMISSION_PERCENTAGE / 100)
    #         Transaction.objects.create(
    #             user=trip.organizer.renter.influencer.user,
    #             amount=influencer_amount,
    #             transaction_type='influencer_income',
    #             trip=trip,
    #             status='completed'
    #         )
    #
    # @action(detail=True, methods=['post'])
    # def cancel(self, request, pk=None):
    #     trip = self.get_object()
    #     if trip.status != 'current':
    #         return Response({"error": "Отмена возможна только для текущих поездок"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     now = timezone.now()
    #     start_date = timezone.make_aware(datetime.combine(trip.start_date, time.min))
    #     if (start_date - now).days < 2:
    #         return Response({"error": "Отмена невозможна менее чем за 48 часов до начала поездки"},
    #                         status=status.HTTP_400_BAD_REQUEST)
    #
    #     deposit_transaction = Transaction.objects.filter(request_rent__trips=trip, transaction_type='deposit').first()
    #     if deposit_transaction:
    #         tinkoff_service = TinkoffPaymentService()
    #         refund = tinkoff_service.refund(deposit_transaction.tinkoff_payment_id, deposit_transaction.amount)
    #         if refund.get('Success'):
    #             deposit_transaction.status = 'refunded'
    #             deposit_transaction.save()
    #             trip.status = 'canceled'
    #             trip.save()
    #             return Response({"message": "Поездка отменена, депозит возвращен"})
    #         else:
    #             return Response({"error": "Не удалось вернуть депозит"}, status=status.HTTP_400_BAD_REQUEST)
    #     else:
    #         return Response({"error": "Транзакция депозита не найдена"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(summary="Чат между арендатором и арендодателем", description="""\nЧат между арендатором и арендодателем. 
                                                                                Создается автоматически при создании 
                                                                                поездки. Чат доступен по адресу:\n 
                        wss://<host_name>/ws/chat/<chat_id>/?token=<JWT>&lang=<lang>""")
class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]

    def get_queryset(self):
        user = self.request.user
        return Chat.objects.filter(participants=user)


@extend_schema(summary="Сообщения чата арендодателя и арендатора", description="Сообщения чата арендодателя и "
                                                                               "арендатора")
class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsAdminOrOwner]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MessageFilter
    ordering_fields = ['timestamp']

    def get_queryset(self):
        user = self.request.user
        return Message.objects.filter(chat__participants=user)


@extend_schema(summary="Заявка на аренду", description="Заявка на аренду. Создать может только пользователь renter.\
                                                После создания пользователь, который является владельцем транспорта,\
                                                может обновить статус заявки - принять или отклонить (accept|denied).\
                                                При изменении статуса на accept автоматически создается поездка Trip)")
class RequestRentViewSet(viewsets.ModelViewSet):
    serializer_class = RequestRentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        content_types = {
            'Auto': ContentType.objects.get_for_model(Auto),
            'Bike': ContentType.objects.get_for_model(Bike),
            'Ship': ContentType.objects.get_for_model(Ship),
            'Helicopter': ContentType.objects.get_for_model(Helicopter),
            'SpecialTechnic': ContentType.objects.get_for_model(SpecialTechnic)
        }

        filters = Q(organizer=user)
        for model_name, content_type in content_types.items():
            model = content_type.model_class()
            filters |= Q(content_type=content_type, object_id__in=model.objects.filter(owner=user).values('id'))

        return RequestRent.objects.filter(filters)

    def check_permissions(self, request):
        user = self.request.user
        if hasattr(user, 'lessor') and request.method in ['POST']:
            raise PermissionDenied("Арендодатели не могут создавать заявки на аренду.")
        if hasattr(user, 'renter') and request.method in ['PATCH', 'PUT']:
            raise PermissionDenied("Арендаторы не могут обновлять заявки на аренду.")
        super().check_permissions(request)

    def create(self, request, *args, **kwargs):
        self.check_permissions(request)
        vehicle_type = request.data.get('vehicle_type')
        object_id = request.data.get('vehicle_id')

        if not vehicle_type:
            raise DRFValidationError("Требуется указать тип транспортного средства.")
        if not object_id:
            raise DRFValidationError("Требуется идентификатор объекта.")

        vehicle_type = vehicle_type.lower()
        model_mapping = {
            'auto': Auto,
            'bike': Bike,
            'ship': Ship,
            'helicopter': Helicopter,
            'specialtechnic': SpecialTechnic
        }

        model = model_mapping.get(vehicle_type)

        if not model:
            raise DRFValidationError(f"Недопустимый тип транспортного средства: {vehicle_type}")

        try:
            vehicle_instance = model.objects.get(id=object_id)
        except model.DoesNotExist:
            raise DRFValidationError(f"Транспортное средство с идентификатором {object_id} не существует.")

        availability = vehicle_instance.availability

        # Проверка доступности
        if availability.on_request:
            request_start_date = None
            request_end_date = None
        else:
            request_start_date = request.data.get('start_date')
            request_end_date = request.data.get('end_date')

            if not request_start_date:
                raise DRFValidationError("Обязательна дата начала.")
            if not request_end_date:
                raise DRFValidationError("Обязательна дата окончания.")

            # Преобразование строк в объекты даты
            try:
                request_start_date = datetime.strptime(request_start_date, '%Y-%m-%d').date()
                request_end_date = datetime.strptime(request_end_date, '%Y-%m-%d').date()
            except ValueError:
                raise DRFValidationError("Неверный формат даты. Ожидается YYYY-MM-DD.")

            # Проверка доступности по датам
            availabilities = list(vehicle_instance.availabilities.values('start_date', 'end_date'))
            if not availabilities:
                raise DRFValidationError("Не найдено доступных дат для этого транспорта.")

            # Преобразование дат в строки
            for availability in availabilities:
                availability['start_date'] = availability['start_date'].strftime('%Y-%m-%d')
                availability['end_date'] = availability['end_date'].strftime('%Y-%m-%d')

            sub_period = {'start_date': request_start_date, 'end_date': request_end_date}

            if not is_period_contained(availabilities, sub_period):
                raise DRFValidationError("Запрашиваемый период недоступен для данного транспортного средства.")

            # Проверка на допустимый период аренды
            rental_days = (request_end_date - request_start_date).days + 1
            min_days = vehicle_instance.min_rent_day
            max_days = vehicle_instance.max_rent_day

            if rental_days < min_days or rental_days > max_days:
                warning_message = (
                    f"Период аренды должен быть между {min_days} и {max_days} днями. "
                    f"Текущий период: {rental_days} дней."
                )
                return Response({'warning': warning_message}, status=status.HTTP_400_BAD_REQUEST)

        # Проверка возраста и опыта водителя
        if vehicle_instance.drivers_age:
            if request.user.date_of_birth:
                user_age = calculate_age(request.user.date_of_birth)
                if user_age < vehicle_instance.drivers_age:
                    raise DRFValidationError(
                        "Пользователь не соответствует возрастным требованиям, предъявляемым к данному транспортному средству.")
            else:
                raise DRFValidationError(
                    "Пользователь не соответствует возрастным требованиям, предъявляемым к данному транспортному средству.")

        if vehicle_instance.drivers_experience:
            driver_license = RenterDocuments.objects.filter(renter=request.user.renter, title='license').first()
            if not driver_license:
                raise DRFValidationError("У пользователя не найдено водительского удостоверения.")

            issue_date = driver_license.issue_date
            if issue_date:
                years_of_experience = (date.today() - issue_date).days // 365
                if years_of_experience < vehicle_instance.drivers_experience:
                    raise DRFValidationError(
                        "Пользователь не соответствует требованиям водительского стажа, предъявляемым к данному транспортному средству.")
            else:
                raise DRFValidationError("Дата выдачи водительского удостоверения не указана.")

        if vehicle_instance.drivers_only_verified and not request.user.renter.verification:
            raise DRFValidationError("Транспорт сдается только верифицированным пользователям.")

        if vehicle_instance.drivers_rating and vehicle_instance.drivers_rating > request.user.renter.get_average_rating() and request.user.renter.get_average_rating() != 0:
            raise DRFValidationError(f"Требуемый рейтинг для аренды транспорта: {vehicle_instance.drivers_rating}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_rent = serializer.save()

        # Отправка уведомлений
        url = f'{settings.HOST_URL}/chat/request_rents/{request_rent.id}'
        content = f'Вам поступила заявка на аренду {vehicle_instance}'
        Notification.objects.create(user=vehicle_instance.owner, content=content, url=url)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # @action(detail=True, methods=['post'])
    # def pay_deposit(self, request, pk=None):
    #     request_rent = self.get_object()
    #     if request_rent.deposit_paid:
    #         return Response({"error": "Депозит уже оплачен"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     tinkoff_service = TinkoffPaymentService()
    #     deposit_amount = request_rent.total_cost * Decimal('0.3')  # 30% от общей стоимости
    #     if request_rent.delivery_cost:
    #         deposit_amount += request_rent.delivery_cost
    #
    #     payment = tinkoff_service.init_payment(
    #         amount=deposit_amount,
    #         order_id=f"deposit-{request_rent.id}",
    #         description=f"Депозит за аренду {request_rent.vehicle}"
    #     )
    #
    #     if payment.get('Success'):
    #         Transaction.objects.create(
    #             user=request.user,
    #             amount=deposit_amount,
    #             transaction_type='deposit',
    #             request_rent=request_rent,
    #             tinkoff_payment_id=payment['PaymentId'],
    #             status='pending'
    #         )
    #         return Response({"payment_url": payment['PaymentURL']})
    #     else:
    #         return Response({"error": "Не удалось инициировать платеж"}, status=status.HTTP_400_BAD_REQUEST)
    #
    # @action(detail=True, methods=['post'])
    # def confirm_deposit(self, request, pk=None):
    #     request_rent = self.get_object()
    #     transaction = Transaction.objects.filter(request_rent=request_rent, transaction_type='deposit').last()
    #
    #     if not transaction:
    #         return Response({"error": "Транзакция не найдена"}, status=status.HTTP_400_BAD_REQUEST)
    #
    #     tinkoff_service = TinkoffPaymentService()
    #     payment_status = tinkoff_service.check_payment_status(transaction.tinkoff_payment_id)
    #
    #     if payment_status.get('Status') == 'CONFIRMED':
    #         transaction.status = 'completed'
    #         transaction.save()
    #         request_rent.deposit_paid = True
    #         request_rent.save()
    #         return Response({"message": "Депозит успешно оплачен"})
    #     else:
    #         return Response({"error": "Платеж не подтвержден"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        instance = self.get_object()
        if 'status' in self.request.data:
            new_status = self.request.data['status']
            if new_status == 'accept':
                if instance.owner != self.request.user:
                    raise DRFValidationError("Только владелец транспортного средства может принять запрос.")
                if not instance.deposit_paid:
                    raise ValidationError("Депозит должен быть оплачен перед принятием заявки.")

                model = instance.content_type.model_class()
                object_id = instance.object_id
                try:
                    vehicle_instance = model.objects.get(id=object_id)
                except model.DoesNotExist:
                    raise DRFValidationError(f"Транспорт с ID {object_id} не найден.")

                availabilities = list(vehicle_instance.availabilities.values('start_date', 'end_date'))
                if not availabilities:
                    raise DRFValidationError("Данных о наличии свободных периодов аренды для этого транспорта не найдено.")

                # Преобразование дат в строки
                for availability in availabilities:
                    availability['start_date'] = availability['start_date'].strftime('%Y-%m-%d')
                    availability['end_date'] = availability['end_date'].strftime('%Y-%m-%d')

                sub_period = {'start_date': instance.start_date.strftime('%Y-%m-%d'),
                              'end_date': instance.end_date.strftime('%Y-%m-%d')}
                new_availabilities = subtract_periods(availabilities, sub_period)

                if isinstance(new_availabilities, str):
                    raise DRFValidationError(new_availabilities)

                # Обновление или создание новых объектов Availability
                vehicle_instance.availabilities.all().delete()
                for availability in new_availabilities:
                    Availability.objects.create(
                        vehicle=vehicle_instance,
                        start_date=availability['start_date'],
                        end_date=availability['end_date']
                    )

                # Здесь Trip будет создан в модели RequestRent
                serializer.save(user=self.request.user)

                url = f'{settings.HOST_URL}/chat/request_rents/{instance.id}'
                content = f'Заявка на аренду {vehicle_instance} одобрена. Дата начала {instance.start_date}'
                Notification.objects.create(user=instance.organizer, content=content, url=url)
        else:
            serializer.save(user=self.request.user)

    def partial_update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().partial_update(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        self.check_permissions(request)
        return super().update(request, *args, **kwargs)


@extend_schema(summary="Тема чата с техподдержкой", description="Тема чата с техподдержкой")
class TopicSupportViewSet(viewsets.ModelViewSet):
    queryset = TopicSupport.objects.all()
    serializer_class = TopicSupportSerializer
    permissions = [IsAuthenticated]


@extend_schema(summary="Чат с техподдержкой", description="""\nЧат с техподдержкой. Доступен по адресу:\n
                    wss://<host_name>/ws/support_chat/<chat_id>/?token=<JWT>&lang=<lang>""")
class ChatSupportViewSet(viewsets.ModelViewSet):

    serializer_class = ChatSupportSerializer
    permission_classes = [IsAuthenticated, IsChatCreatorOrAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return ChatSupport.objects.all()
        else:
            return ChatSupport.objects.filter(creator=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        messages = MessageSupport.objects.filter(support_chat=instance)
        message_serializer = MessageSupportSerializer(messages, many=True)
        data['messages'] = message_serializer.data

        data['topic_name'] = instance.topic.name if instance.topic else None
        return Response(data)


@extend_schema(summary="Сообщения чата техподдержки", description="Сообщения чата техподдержки")
class MessageSupportViewSet(viewsets.ModelViewSet):
    queryset = MessageSupport.objects.all()
    serializer_class = MessageSupportSerializer
    permission_classes = [IsParticipantOrAdmin]

    def create(self, request, *args, **kwargs):
        chat = self.get_object()
        content = request.data.get('content')
        message = MessageSupport.objects.create(support_chat=chat, sender=request.user, content=content)
        serializer = MessageSupportSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(summary="Отзывы", description="Отзывы к транспорту может оставлять только пользователь, который "
                                             "пользовался транспортом, только после завершения поездки и только один "
                                             "отзыв к одному транспорту. Отвечать на отзывы может только хозяин "
                                             "транспорта")
class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related('user', 'content_type').all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = FeedbackFilter
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_serializer_class(self):
        if self.action in ['create']:
            return FeedbackCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FeedbackUpdateSerializer
        return FeedbackSerializer

    def perform_create(self, serializer):
        content_type_id = serializer.validated_data['content_type'].id
        object_id = serializer.validated_data['object_id']

        # Проверка, оставлял ли уже пользователь отзыв для данного транспортного средства
        existing_feedback = Feedback.objects.filter(
            user=self.request.user,
            content_type_id=content_type_id,
            object_id=object_id
        ).exists()

        if existing_feedback:
            raise serializers.ValidationError("Вы уже оставили отзыв для данного транспортного средства.")

        try:
            trip = Trip.objects.get(
                organizer=self.request.user,
                content_type_id=content_type_id,
                object_id=object_id
            )
        except Trip.DoesNotExist:
            raise serializers.ValidationError(
                "Для того чтобы оставить отзыв, нужно воспользоваться данным транспортом.")

        if trip.status != 'finished':
            raise serializers.ValidationError("Поездка не была завершена.")

        # Получение экземпляра транспортного средства
        vehicle_instance = ContentType.objects.get_for_id(content_type_id).model_class().objects.get(id=object_id)

        serializer.save(user=self.request.user, content_type_id=content_type_id, object_id=object_id)

        # Отправка уведомлений
        content = f'Добавлен отзыв для транспорта {vehicle_instance}'
        url = f'{settings.HOST_URL}/chat/feedbacks/{object_id}'
        Notification.objects.create(user=vehicle_instance.owner, content=content, url=url)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if 'answer' in request.data:
            if instance.vehicle.owner != request.user:
                raise serializers.ValidationError("Только владелец транспорта может оставлять ответы на отзывы.")
            instance.answer = request.data['answer']
            instance.save()
            return Response(FeedbackSerializer(instance).data)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

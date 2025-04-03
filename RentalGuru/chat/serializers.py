from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from RentalGuru.settings import HOST_URL
from feedback.models import Feedback
from influencer.utils import check_promocode
from notification.models import Notification
from payment.TinkoffClient import TinkoffAPI
from payment.models import Payment
from vehicle.models import RatingUpdateLog, Auto, Bike, Ship, Helicopter, SpecialTechnic
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, IssueSupport


class TripSerializer(serializers.ModelSerializer):
    set_rating = serializers.SerializerMethodField()
    set_feedback = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = ['id', 'chat', 'organizer', 'content_type', 'object_id', 'start_time', 'end_time', 'start_date',  'end_date', 'total_cost', 'status', 'set_rating', 'set_feedback', 'owner_name']
        read_only_fields = ['id', 'chat', 'organizer', 'content_type', 'object_id', 'start_time', 'end_time', 'start_date',  'end_date', 'total_cost', 'set_rating', 'set_feedback', 'owner_name']

    def get_set_rating(self, instance):
        return RatingUpdateLog.objects.filter(
            user=instance.organizer,
            content_type=instance.content_type,
            object_id=instance.object_id
        ).exists()

    def get_owner_name(self, instance):
        vehicle = instance.vehicle
        if vehicle and hasattr(vehicle, 'owner'):
            return vehicle.owner.first_name
        return None

    def get_set_feedback(self, instance):
        return Feedback.objects.filter(
            user=instance.organizer,
            content_type=instance.content_type,
            object_id=instance.object_id
        ).exists()

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organizer'] = request.user
        return super().create(validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['content_type'] = instance.content_type.model

        request_rent = RequestRent.objects.filter(chat=instance.chat).first()
        payment = Payment.objects.filter(request_rent=request_rent).first()
        representation['payment_id'] = payment.id if payment else None
        representation['amount'] = payment.amount if payment else None
        return representation

    def _process_influencer_payment(self, influencer, request_rent):
        if influencer:
            payment = Payment.objects.get(request_rent=request_rent)
            cash = Decimal(payment.amount) / 100 * Decimal(influencer.commission)
            influencer.account += cash
            influencer.save()

    def update(self, instance, validated_data):
        request = self.context.get('request')
        previous_status = instance.status
        new_status = validated_data.get('status', previous_status)

        # Отмена поездки
        if previous_status != 'canceled' and new_status == 'canceled':

            # Проверка доступа
            if request.user != instance.organizer and request.user.role not in ['admin', 'manager']:
                raise serializers.ValidationError({"detail": "Вы не можете отменить поездку."})

            # Возврат средств
            request_rent = RequestRent.objects.filter(chat=instance.chat).first()
            if not request_rent:
                raise serializers.ValidationError({"detail": "Заявка на аренду не найдена."})

            payment = Payment.objects.filter(request_rent=request_rent).first()
            if not payment:
                raise serializers.ValidationError({"detail": "Платеж не найден."})

            if payment.status == 'success' and instance.get_time_until_start().total_seconds() / 3600 > 48:
                refund = TinkoffAPI()
                response = refund.cancel_payment(payment.payment_id, payment.amount)
                if response.get("Success"):
                    payment.status = 'canceled'
                    payment.save()

                    Notification.objects.create(
                        user=instance.organizer,
                        content=f"Поездка c транспортом {instance.vehicle} была отменена. Будет произведен возврат средств в количестве {payment.amount} р."
                    )

            else:
                Notification.objects.create(
                    user=instance.organizer,
                    content=f"Поездка c транспортом {instance.vehicle} была отменена."
                )
            Notification.objects.create(
                user=instance.vehicle.owner,
                content=f"Поездка c транспортом {instance.vehicle} была отменена."
            )
        instance = super().update(instance, validated_data)

        # Завершение поездки
        if previous_status != 'finished' and new_status == 'finished':
            Notification.objects.create(
                user=instance.organizer,
                content=f"Поездка c транспортом {instance.vehicle} была завершена. Оцените вашу поездку"
            )
            rating = RatingUpdateLog.objects.filter(user=instance.organizer, content_type=instance.content_type, object_id=instance.object_id).exists()
            feedback = Feedback.objects.filter(user=instance.organizer, content_type=instance.content_type, object_id=instance.object_id).exists()
            Notification.objects.create(
                user=instance.vehicle.owner,
                content=f"Поездка c транспортом {instance.vehicle} была завершена. Оцените вашу поездку",
                url=f"{HOST_URL}/?trip={instance.id}&trip_start_time={instance.start_time}&trip_start_date={instance.start_date}&trip_end_date={instance.end_date}&trip_end_time={instance.end_time}&vehicle={instance.vehicle}&vehicle_id={instance.object_id}&vehicle_type={instance.content_type.model}&user_id={instance.organizer.id}&user_avater={instance.organizer.avatar}&rating={rating}&feedback={feedback}"
            )

            # Начисление средств партнеру
            request_rent = instance.chat.request_rent
            self._process_influencer_payment(getattr(instance.organizer.renter, 'influencer', None), request_rent)
            self._process_influencer_payment(getattr(instance.vehicle.owner.lessor, 'influencer', None), request_rent)

        return instance


class RequestRentSerializer(serializers.ModelSerializer):
    vehicle_type = serializers.CharField(write_only=True)
    vehicle_id = serializers.IntegerField(write_only=True)
    promocode = serializers.CharField(required=False, allow_blank=True)
    bonus = serializers.IntegerField(required=False, allow_null=True)
    chat_id = serializers.SerializerMethodField()

    class Meta:
        model = RequestRent
        exclude = ['content_type', 'object_id']
        read_only_fields = ['organizer', 'total_cost', 'deposit_cost', 'delivery_cost']

    def create(self, validated_data):
        query_promocode = validated_data.pop('promocode', None)
        bonus = validated_data.pop('bonus', None)
        vehicle_type = validated_data.pop('vehicle_type')
        vehicle_id = validated_data.pop('vehicle_id')

        try:
            content_type = ContentType.objects.get(model=vehicle_type)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({"vehicle_type": "Недопустимый тип объекта."})

        validated_data['content_type'] = content_type
        validated_data['object_id'] = vehicle_id
        validated_data['status'] = 'unknown'
        validated_data['is_deleted'] = False
        request = self.context.get('request')
        validated_data['organizer'] = request.user
        renter = validated_data['organizer'].renter

        # Обработка промокодов
        if query_promocode:
            promo_code = check_promocode(request.user, query_promocode)
            if isinstance(promo_code, str):
                raise serializers.ValidationError({"message": promo_code})
            validated_data['promocode'] = promo_code

        # Обработка бонусов
        if bonus:
            if renter.bonus_account < bonus:
                raise serializers.ValidationError({"message": "На бонусном счете недостаточно средств"})
            else:
                validated_data['bonus'] = bonus

        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'vehicle_type' in validated_data:
            vehicle_type = validated_data.pop('vehicle_type')
            try:
                content_type = ContentType.objects.get(model=vehicle_type)
            except ContentType.DoesNotExist:
                raise serializers.ValidationError({"vehicle_type": "Недопустимый тип объекта."})
            validated_data['content_type'] = content_type

        if 'vehicle_id' in validated_data:
            vehicle_id = validated_data.pop('vehicle_id')
            validated_data['object_id'] = vehicle_id

        return super().update(instance, validated_data)

    def get_chat_id(self, obj):
        if obj.on_request:
            try:
                return obj.chat.id
            except (Chat.DoesNotExist, AttributeError):
                return None
        return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['vehicle_type'] = instance.content_type.model
        representation['vehicle_id'] = instance.object_id

        if hasattr(instance, 'prefetched_payment_amount'):
            representation['amount'] = instance.prefetched_payment_amount
        else:
            payment = Payment.objects.filter(request_rent=instance).first()
            representation['amount'] = payment.amount if payment else None

        if hasattr(instance, 'renter_id') and instance.renter_id:

            renter = None
            if hasattr(instance, '_prefetched_renter'):
                renter = instance._prefetched_renter

            if renter:
                representation['renter_avatar'] = renter.avatar.url if renter.avatar else None
                representation['renter_first_name'] = renter.first_name
                representation['renter_last_name'] = renter.last_name

        if instance.status == 'accept' and hasattr(instance, 'prefetched_payment_id'):
            representation['payment_id'] = instance.prefetched_payment_id

        return representation

    def validate(self, data):
        status = data.get('status')
        denied_reason = data.get('denied_reason')

        if status == 'denied' and not denied_reason:
            raise serializers.ValidationError({
                'denied_reason': 'Необходимо указать причину отказа, если статус — "denied".'
            })
        if status != 'denied' and denied_reason:
            raise serializers.ValidationError({
                'denied_reason': 'Причина отказа может быть указана только при статусе "denied".'
            })

        return data


class BaseMessageSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['sender'] = request.user
        if 'file' in validated_data:
            file = validated_data.pop('file')
            validated_data['file'] = file
        return super().create(validated_data)

    class Meta:
        abstract = True


class ChatSerializer(serializers.ModelSerializer):
    participants = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'request_rent', 'participants', 'last_message']

    def get_participants(self, obj):
        current_user = self.context['request'].user
        other_participants = obj.participants.exclude(id=current_user.id)

        return [
            {
                "id": participant.id,
                "first_name": participant.first_name,
                "avatar": participant.avatar.url if participant.avatar else None
            }
            for participant in other_participants
        ]

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()
        if last_message:
            return {
                "id": last_message.id,
                "content": last_message.content,
                "sender": {
                    "id": last_message.sender.id,
                    "first_name": last_message.sender.first_name,
                    "avatar": last_message.sender.avatar.url if last_message.sender.avatar else None
                },
                "timestamp": last_message.timestamp
            }
        return None


class MessageSerializer(BaseMessageSerializer):
    sender_avatar = serializers.SerializerMethodField()
    sender_first_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender']

    @extend_schema_field(serializers.ImageField())
    def get_sender_avatar(self, obj):
        if obj.sender.avatar:
            return obj.sender.avatar.url
        return None

    @extend_schema_field(serializers.CharField())
    def get_sender_first_name(self, obj):
        return obj.sender.first_name


# Чат с техподдержкой

class MessageSupportSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = MessageSupport
        fields = ['id', 'chat', 'sender', 'sender_name', 'content', 'timestamp', 'file', 'deleted']
        read_only_fields = ['id', 'timestamp']


class TopicSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicSupport
        fields = ['id', 'name', 'count']
        read_only_fields = ['id', 'count']


class IssueSupportSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(write_only=True)

    class Meta:
        model = IssueSupport
        fields = ['id', 'topic_name', 'description']

    def create(self, validated_data):
        user = self.context['request'].user
        chat, created = ChatSupport.objects.get_or_create(creator=user)
        topic_name = validated_data.pop('topic_name')
        topic, created = TopicSupport.objects.get_or_create(name=topic_name)

        if created:
            topic.count = 1
        else:
            topic.count += 1
        topic.save()

        issue = IssueSupport.objects.create(chat=chat, topic=topic, **validated_data)

        return issue


class ChatSupportSerializer(serializers.ModelSerializer):
    issues = IssueSupportSerializer(many=True, read_only=True)
    messages = MessageSupportSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSupport
        fields = ['id', 'creator', 'issues', 'messages', 'last_message']

    def get_last_message(self, obj):
        last_message = obj.message_support.order_by('-timestamp').first()
        if last_message:
            return {
                "id": last_message.id,
                "content": last_message.content,
                "sender": {
                    "id": last_message.sender.id,
                    "first_name": last_message.sender.first_name,
                    "avatar": last_message.sender.avatar.url if last_message.sender.avatar else None
                },
                "timestamp": last_message.timestamp
            }
        return None


class ChatSupportRetrieveSerializer(serializers.ModelSerializer):
    last_issue = serializers.SerializerMethodField()

    class Meta:
        model = ChatSupport
        fields = ['id', 'creator', 'last_issue']

    def get_last_issue(self, obj):
        """ Возвращает последнее обращение для чата. """
        last_issue = IssueSupport.objects.filter(chat=obj).order_by('-created_at').first()
        if last_issue:
            return IssueSupportSerializer(last_issue).data
        return None


class VehicleRelatedField(serializers.Field):
    def to_representation(self, value):
        return {
            'id': value.id,
            'type': value._meta.model_name,
            'name': str(value)
        }

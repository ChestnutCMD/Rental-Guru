from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from vehicle.models import RatingUpdateLog
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, Feedback


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['id', 'status', 'organizer', 'content_type', 'object_id', 'start_date', 'end_date', 'total_cost']
        read_only_fields = ['id', 'organizer', 'content_type', 'object_id', 'start_date', 'end_date', 'total_cost']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organizer'] = request.user
        return super().create(validated_data)


class RequestRentSerializer(serializers.ModelSerializer):
    vehicle_type = serializers.CharField(write_only=True)
    vehicle_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = RequestRent
        exclude = ['content_type', 'object_id']
        read_only_fields = ['organizer', 'total_cost', 'deposit_paid', 'delivery_cost']

    def create(self, validated_data):
        vehicle_type = validated_data.pop('vehicle_type')
        vehicle_id = validated_data.pop('vehicle_id')

        try:
            content_type = ContentType.objects.get(model=vehicle_type)
        except ContentType.DoesNotExist:
            raise serializers.ValidationError({"vehicle_type": "Недопустимый тип объекта."})

        validated_data['content_type'] = content_type
        validated_data['object_id'] = vehicle_id
        validated_data['status'] = 'unknown'
        request = self.context.get('request')
        validated_data['organizer'] = request.user

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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['vehicle_type'] = instance.content_type.model
        representation['vehicle_id'] = instance.object_id
        return representation


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
        fields = ['id', 'trip', 'participants', 'last_message']

    def get_participants(self, obj):
        return [
            {
                "id": participant.id,
                "first_name": participant.first_name,
                "avatar": participant.avatar.url if participant.avatar else None
            }
            for participant in obj.participants.all()
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

class MessageSupportSerializer(BaseMessageSerializer):
    class Meta:
        model = MessageSupport
        fields = '__all__'
        read_only_fields = ['sender']


class TopicSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TopicSupport
        fields = ['id', 'name', 'count']


class ChatSupportSerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(write_only=True, required=False)
    message = serializers.CharField(write_only=True)
    creator = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = ChatSupport
        fields = ['id', 'topic_name', 'message', 'creator']
        read_only_fields = ['id', 'creator']

    def validate(self, attrs):
        if not attrs.get('topic') and not attrs.get('topic_name'):
            raise serializers.ValidationError("Either topic or topic_name must be provided.")
        return attrs

    def create(self, validated_data):
        topic_name = validated_data.pop('topic_name', None)
        message_content = validated_data.pop('message')
        creator = validated_data.pop('creator')

        if topic_name:
            topic, created = TopicSupport.objects.get_or_create(name=topic_name)
            if created:
                topic.count = 1
            else:
                topic.count += 1
            topic.save()
            validated_data['topic'] = topic

        chat = ChatSupport.objects.create(creator=creator, **validated_data)
        chat.participants.add(creator)

        MessageSupport.objects.create(support_chat=chat, sender=creator, content=message_content)

        return chat


class ChatSupportRetrieveSerializer(serializers.ModelSerializer):
    topic = TopicSupportSerializer()
    messages = MessageSupportSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSupport
        fields = ['id', 'topic', 'participants', 'messages']
        read_only_fields = ['id', 'participants']


class VehicleRelatedField(serializers.Field):
    def to_representation(self, value):
        return {
            'id': value.id,
            'type': value._meta.model_name,
            'name': str(value)
        }


class FeedbackCreateSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField()

    class Meta:
        model = Feedback
        fields = ['id', 'content', 'content_type', 'object_id']

    def validate_content_type(self, value):
        try:
            content_type = ContentType.objects.get(model=value.lower())
        except ContentType.DoesNotExist:
            raise serializers.ValidationError("Указанный тип контента не существует.")
        return content_type

    def create(self, validated_data):
        content_type = validated_data.pop('content_type')
        validated_data['content_type'] = content_type
        return super().create(validated_data)


class FeedbackUpdateSerializer(serializers.ModelSerializer):
    answer = serializers.CharField(required=True)

    class Meta:
        model = Feedback
        fields = ['answer']

    def validate_answer(self, value):
        request = self.context.get('request')
        if self.instance.vehicle.owner != request.user:
            raise serializers.ValidationError("Только владелец транспорта может оставлять ответы на отзывы.")
        return value


class FeedbackSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    answer = serializers.CharField(required=False, allow_blank=True)
    vehicle = VehicleRelatedField()
    average_ratings = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'content', 'answer', 'content_type', 'object_id', 'vehicle', 'average_ratings', 'timestamp']

    def get_user(self, obj):
        if obj.user:
            return {
                "id": obj.user.id,
                "first_name": obj.user.first_name,
                "avatar": obj.user.avatar.url if obj.user.avatar else None
            }
        return None

    def get_average_ratings(self, obj):
        content_type = ContentType.objects.get_for_model(obj.vehicle)

        try:
            log = RatingUpdateLog.objects.get(
                user=obj.user,
                content_type=content_type,
                object_id=obj.vehicle.id
            )

            ratings_sum = (
                (log.cleanliness or 0) +
                (log.maintenance or 0) +
                (log.communication or 0) +
                (log.convenience or 0) +
                (log.accuracy or 0)
            )
            average_rating = ratings_sum / 5
            return round(average_rating, 2)
        except RatingUpdateLog.DoesNotExist:
            return None

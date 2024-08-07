from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport, Feedback


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['organizer']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organizer'] = request.user
        return super().create(validated_data)


class RequestRentSerializer(serializers.ModelSerializer):
    vehicle_type = serializers.CharField(write_only=True)
    vehicle_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = RequestRent
        exclude = ['content_type', 'object_id']  # Исключаем content_type и object_id
        read_only_fields = ['organizer']

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
    class Meta:
        model = Chat
        fields = '__all__'


class MessageSerializer(BaseMessageSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender']


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
        fields = ['id', 'topic', 'topic_name', 'message', 'creator']
        read_only_fields = ['participants']

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

        # Создание первого сообщения
        MessageSupport.objects.create(support_chat=chat, sender=creator, content=message_content)

        return chat


class ChatSupportRetrieveSerializer(serializers.ModelSerializer):
    topic = TopicSupportSerializer()
    messages = MessageSupportSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSupport
        fields = ['id', 'topic', 'participants', 'messages']
        read_only_fields = ['participants']


class VehicleRelatedField(serializers.Field):
    def to_representation(self, value):
        return {
            'id': value.id,
            'type': value._meta.model_name,
            'name': str(value)
        }


class FeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'content', 'content_type', 'object_id']

    def validate_content_type(self, value):
        try:
            return ContentType.objects.get(model=value).id
        except ContentType.DoesNotExist:
            raise serializers.ValidationError("Указанный тип контента не существует.")


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

    class Meta:
        model = Feedback
        fields = ['id', 'user', 'content', 'answer', 'content_type', 'object_id', 'vehicle']

    def get_user(self, obj):
        return obj.user.first_name if obj.user else None
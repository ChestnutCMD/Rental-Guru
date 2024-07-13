from rest_framework import serializers
from .models import Trip, Chat, Message, RequestRent, TopicSupport, ChatSupport, MessageSupport


class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['organizer']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organizer'] = request.user
        return super().create(validated_data)


class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = '__all__'


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['sender'] = request.user
        return super().create(validated_data)


class RequestRentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestRent
        fields = '__all__'

    def get_fields(self, *args, **kwargs):
        fields = super().get_fields(*args, **kwargs)
        if self.instance:  # Если это обновление
            for field in fields:
                if field != 'status':
                    fields[field].read_only = True
        return fields

    def create(self, validated_data):
        if validated_data.get('status') != 'unknown':
            validated_data['status'] = 'unknown'
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Проверяем, что только поле status может быть обновлено
        if 'status' in validated_data:
            instance.status = validated_data.get('status', instance.status)
            instance.save(user=self.context['request'].user)
        return instance

# Чат с техподдержкой


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


class MessageSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageSupport
        fields = ['id', 'support_chat', 'sender', 'content', 'timestamp']


class ChatSupportRetrieveSerializer(serializers.ModelSerializer):
    topic = TopicSupportSerializer()
    messages = MessageSupportSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSupport
        fields = ['id', 'topic', 'participants', 'messages']
        read_only_fields = ['participants']

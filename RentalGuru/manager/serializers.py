from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from rest_framework import serializers

from app.models import User
from franchise.models import Franchise, City
from manager.models import AccessType, Manager, ManagerDocuments
from manager.utils import generate_secure_password
from notification.models import Notification


class ManagerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerDocuments
        fields = ['number', 'photo']


class AccessTypeSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с типами доступа"""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = AccessType
        fields = ['id', 'name', 'permission', 'display_name']

    def get_display_name(self, obj):
        name_display = dict(AccessType.TYPE_CHOICES).get(obj.name, obj.name)
        permission_display = dict(AccessType.PERMISSION_CHOICES).get(obj.permission, obj.permission)
        return f"{name_display} — {permission_display}"


class ManagerListSerializer(serializers.ModelSerializer):
    """ Сериализато списка менеджеров """
    full_name = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    telephone = serializers.CharField(source='user.telephone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    access_types = AccessTypeSerializer(many=True, read_only=True)

    class Meta:
        model = Manager
        fields = ['id', 'full_name', 'avatar', 'telephone', 'email', 'city', 'access_types']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class ManagerDetailSerializer(serializers.ModelSerializer):
    """ Сериализато детального отображения менеджера """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    telephone = serializers.CharField(source='user.telephone', read_only=True)
    date_of_birth = serializers.DateField(source='user.date_of_birth', read_only=True)
    document_photo = serializers.ImageField(source='manager_document.photo', read_only=True)
    document_number = serializers.CharField(source='manager_document.number', read_only=True)
    access_types = AccessTypeSerializer(many=True, read_only=True)

    city_name = serializers.CharField(source='city.title', read_only=True)

    class Meta:
        model = Manager
        fields = [
            'id',
            'user_id',
            'first_name',
            'last_name',
            'avatar',
            'email',
            'telephone',
            'date_of_birth',
            'document_photo',
            'document_number',
            'access_types',
            'city_name',
        ]


class ManagerCreateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    telephone = serializers.CharField(write_only=True, required=False)
    city_id = serializers.IntegerField(write_only=True, required=False)
    access_types = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Manager
        fields = ['id', 'email', 'first_name', 'last_name', 'telephone', 'city_id', 'access_types']

    def create(self, validated_data):
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        telephone = validated_data.pop('telephone', None)
        city_id = validated_data.get('city_id')
        access_types_data = validated_data.pop('access_types', [])

        request = self.context.get('request')
        if not (request and request.user.role == 'admin'):
            raise serializers.ValidationError("Только администраторы могут создавать менеджеров.")

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже существует."})

        password = generate_secure_password()

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            telephone=telephone,
            password=password,
            role='manager',
        )

        if city_id:
            try:
                city = City.objects.get(id=city_id)
                manager = Manager.objects.create(user=user, city=city)
            except City.DoesNotExist:
                raise serializers.ValidationError({"city_id": "Город с таким ID не найден."})
        else:
            manager = Manager.objects.create(user=user)

        # Добавляем типы доступа
        access_types = []
        for at in access_types_data:
            name = at.get('name')
            permission = at.get('permission')
            if not name or not permission:
                raise serializers.ValidationError(
                    {"access_types": "Каждый элемент должен содержать 'name' и 'permission'."}
                )
            try:
                at_instance = AccessType.objects.get(name=name, permission=permission)
                access_types.append(at_instance)
            except AccessType.DoesNotExist:
                raise serializers.ValidationError(
                    {"access_types": f"Доступ с name={name} и permission={permission} не найден."}
                )

        if access_types:
            manager.access_types.set(access_types)

        content = f"Здравствуйте, {first_name}!\n\nВы были зарегистрированы как менеджер. Ваш пароль для входа: {password}"
        Notification.objects.create(user=user, content=content)
        return manager

class CustomAvatarField(serializers.ImageField):
    def to_internal_value(self, data):
        if data == "" or data is None:
            return None
        return super().to_internal_value(data)


class ManagerUpdateSerializer(serializers.ModelSerializer):
    """ Сериализатор обновления менеджера """
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    avatar = CustomAvatarField(source='user.avatar', required=False)
    telephone = serializers.CharField(source='user.telephone', required=False)
    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False)
    password = serializers.CharField(write_only=True, required=False)
    document = ManagerDocumentSerializer(source='manager_document', required=False)
    access_types = serializers.PrimaryKeyRelatedField(
        queryset=AccessType.objects.all(),
        many=True,
        required=False
    )
    city_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Manager
        fields = [
            'first_name',
            'last_name',
            'avatar',
            'telephone',
            'date_of_birth',
            'password',
            'document',
            'access_types',
            'city_id'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        document_data = validated_data.pop('manager_document', None)
        access_types = validated_data.pop('access_types', None)
        city_id = validated_data.pop('city_id', None)
        user = instance.user

        for field, value in user_data.items():
            if field == 'avatar':
                if value is None:
                    if user.avatar:
                        user.avatar.delete(save=False)
                        user.avatar = None
                else:
                    setattr(user, field, value)
            else:
                setattr(user, field, value)

        if 'password' in validated_data:
            password = validated_data.pop('password')
            user.set_password(password)
            instance.password_updated_at = now()
            instance.save()

        for field, value in user_data.items():
            setattr(user, field, value)
        user.save()

        if document_data:
            defaults = {}
            if 'number' in document_data:
                defaults['number'] = document_data['number']
            if 'photo' in document_data:
                defaults['photo'] = document_data['photo']
            document, created = ManagerDocuments.objects.update_or_create(
                manager=instance,
                defaults=defaults
            )

        # Проверка прав на изменение доступов - только админ может изменять права
        if access_types is not None and self.context['request'].user.role == 'admin':
            instance.access_types.set(access_types)

        if city_id:
            try:
                city = City.objects.get(id=city_id)
                instance.city = city
            except City.DoesNotExist:
                raise serializers.ValidationError({"city_id": "Город с таким ID не найден."})

        instance.save()
        return instance

import random

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now
from rest_framework import serializers

from app.models import User
from franchise.models import Franchise
from manager.models import ManagerPermission, Manager, ManagerDocuments
from notification.models import Notification


class ManagerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerDocuments
        fields = ['number', 'photo']


class ManagerPermissionSerializer(serializers.ModelSerializer):
    """Сериализатор для работы с доступами"""
    model_name = serializers.SerializerMethodField()
    object_display = serializers.SerializerMethodField()
    content_type = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(),
        required=False
    )
    object_id = serializers.IntegerField(required=False, allow_null=True)
    is_global = serializers.BooleanField(default=False)
    manager = serializers.PrimaryKeyRelatedField(
        queryset=Manager.objects.all(),
        required=False
    )
    permission_type = serializers.ChoiceField(
        choices=[
            ('read', 'Чтение'),
            ('edit', 'Редактирование'),
            ('delete', 'Удаление'),
        ],
        required=False
    )

    class Meta:
        model = ManagerPermission
        fields = ['id', 'manager', 'content_type', 'object_id', 'model_name', 'object_display', 'permission_type', 'is_global']

    def to_internal_value(self, data):
        """Обработка данных перед валидацией"""
        data = data.copy()
        if data.get('is_global', False):
            data['object_id'] = None
        return super().to_internal_value(data)

    def validate(self, attrs):
        """Общая валидация для создания и обновления"""
        instance = self.instance

        is_global = attrs.get('is_global', instance.is_global if instance else False)
        content_type = attrs.get('content_type', instance.content_type if instance else None)
        object_id = attrs.get('object_id', instance.object_id if instance else None)

        if not instance:
            if not content_type:
                raise serializers.ValidationError({"content_type": "content_type обязателен при создании."})
            if not attrs.get('manager'):
                raise serializers.ValidationError({"manager": "manager обязателен при создании."})
            if 'permission_type' not in attrs:
                raise serializers.ValidationError({"permission_type": "permission_type обязателен при создании."})

        if is_global:
            attrs['object_id'] = None
        elif object_id is None:
            raise serializers.ValidationError({"object_id": "object_id обязателен для локального доступа."})

        return attrs

    def get_model_name(self, obj):
        return obj.content_type.model if obj.content_type else None

    def get_object_display(self, obj):
        return str(obj.content_object) if obj.content_object else None


class ManagerListSerializer(serializers.ModelSerializer):
    """ Сериализато списка менеджеров """
    full_name = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    telephone = serializers.CharField(source='user.telephone', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Manager
        fields = ['id', 'full_name', 'avatar', 'telephone', 'email']

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"


class ManagerDetailSerializer(serializers.ModelSerializer):
    """ Сериализато детального отображения менеджера """
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    avatar = serializers.ImageField(source='user.avatar', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    telephone = serializers.CharField(source='user.telephone', read_only=True)
    date_of_birth = serializers.DateField(source='user.date_of_birth', read_only=True)
    document_photo = serializers.ImageField(source='manager_document.photo', read_only=True)
    document_number = serializers.CharField(source='manager_document.number', read_only=True)
    permissions = ManagerPermissionSerializer(many=True, read_only=True)

    franchise_name = serializers.CharField(source='franchise.name', read_only=True)
    franchise_city = serializers.CharField(source='franchise.city.name', read_only=True)
    franchise_director = serializers.CharField(source='franchise.director', read_only=True)
    franchise_total_vehicles = serializers.SerializerMethodField()

    class Meta:
        model = Manager
        fields = [
            'id',
            'first_name',
            'last_name',
            'avatar',
            'email',
            'telephone',
            'date_of_birth',
            'document_photo',
            'document_number',
            'permissions',
            'franchise_name',
            'franchise_city',
            'franchise_director',
            'franchise_total_vehicles',
        ]

    def get_franchise_total_vehicles(self, obj):
        if obj.franchise:
            return obj.franchise.get_total_vehicles()
        return 0


class ManagerCreateSerializer(serializers.ModelSerializer):
    """ Сериализатор создания менеджеров """
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    telephone = serializers.CharField(write_only=True, required=False)
    franchise_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Manager
        fields = ['id', 'email', 'first_name', 'last_name', 'telephone', 'franchise_id']

    def create(self, validated_data):
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        telephone = validated_data.pop('telephone', None)
        franchise_id = validated_data.get('franchise_id')

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже существует."})

        password = User.objects.make_random_password()
        digit = random.choice('0123456789')
        position = random.randint(0, len(password))
        password = password[:position] + digit + password[position:]

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            telephone=telephone,
            password=password,
            role='manager',
        )
        if franchise_id:
            try:
                franchise = Franchise.objects.get(id=franchise_id)
                manager = Manager.objects.create(user=user, franchise=franchise)
            except Franchise.DoesNotExist:
                raise serializers.ValidationError({"franchise_id": "Франшиза с таким ID не найдена."})
        else:
            manager = Manager.objects.create(user=user)

        content = f"Здравствуйте, {first_name}!\n\nВы были зарегистрированы как менеджер. Ваш пароль для входа: {password}."
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
    permissions = ManagerPermissionSerializer(many=True, required=False)
    franchise_id = serializers.IntegerField(write_only=True, required=False)

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
            'permissions',
            'franchise_id'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        document_data = validated_data.pop('manager_document', None)
        permissions_data = validated_data.pop('permissions', None)
        franchise_id = validated_data.pop('franchise_id', None)
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

        if permissions_data and self.context['request'].user.role == 'admin':
            instance.permissions.all().delete()
            for perm_data in permissions_data:
                ManagerPermission.objects.create(manager=instance, **perm_data)

        if franchise_id:
            try:
                franchise = Franchise.objects.get(id=franchise_id)
                instance.franchise = franchise
            except Franchise.DoesNotExist:
                raise serializers.ValidationError({"franchise_id": "Франшиза с таким ID не найдена."})

        instance.save()
        return instance

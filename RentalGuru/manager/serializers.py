from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from app.models import User
from manager.models import ManagerPermission, Manager, ManagerDocuments
from notification.models import Notification


class ManagerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerDocuments
        fields = ['number', 'photo']


class ManagerPermissionSerializer(serializers.ModelSerializer):
    """ Сериализатор доступа """
    model_name = serializers.SerializerMethodField()
    object_display = serializers.SerializerMethodField()
    content_type = serializers.PrimaryKeyRelatedField(
        queryset=ContentType.objects.all(),
        required=False,
        allow_null=True,
    )
    object_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = ManagerPermission
        fields = ['id', 'manager', 'content_type', 'object_id', 'model_name', 'object_display', 'permission_type', 'is_global']

    def get_model_name(self, obj):
        return obj.content_type.model

    def get_object_display(self, obj):
        if obj.content_object:
            return str(obj.content_object)
        return None


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
        ]


class ManagerCreateSerializer(serializers.ModelSerializer):
    """ Сериализатор создания менеджеров """
    email = serializers.EmailField(write_only=True)
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    telephone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Manager
        fields = ['id', 'email', 'first_name', 'last_name', 'telephone']

    def create(self, validated_data):
        email = validated_data.pop('email')
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        telephone = validated_data.pop('telephone', None)

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже существует."})

        password = User.objects.make_random_password()

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            telephone=telephone,
            password=password,
            role='manager',
        )

        manager = Manager.objects.create(user=user, **validated_data)
        content = f"Здравствуйте, {first_name}!\n\nВы были зарегистрированы как менеджер в нашей системе. Ваш пароль для входа: {password}\n\nС уважением, Команда RentalGuru."
        Notification.objects.create(user=user, content=content)
        return manager


class ManagerUpdateSerializer(serializers.ModelSerializer):
    """ Сериализатор обновления менеджера """
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)
    avatar = serializers.ImageField(source='user.avatar', required=False)
    telephone = serializers.CharField(source='user.telephone', required=False)
    date_of_birth = serializers.DateField(source='user.date_of_birth', required=False)
    password = serializers.CharField(write_only=True, required=False)
    document = ManagerDocumentSerializer(source='manager_document', required=False)
    permissions = ManagerPermissionSerializer(many=True, required=False)

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
            'permissions'
        ]

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        document_data = validated_data.pop('manager_document', None)
        permissions_data = validated_data.pop('permissions', None)
        user = instance.user

        if 'password' in validated_data:
            password = validated_data.pop('password')
            user.set_password(password)

        for field, value in user_data.items():
            setattr(user, field, value)
        user.save()

        if document_data and self.context['request'].user.role == 'admin':
            document, created = ManagerDocuments.objects.update_or_create(
                manager=instance,
                defaults=document_data
            )

        if permissions_data and self.context['request'].user.role == 'admin':
            instance.permissions.all().delete()
            for perm_data in permissions_data:
                ManagerPermission.objects.create(manager=instance, **perm_data)

        return instance

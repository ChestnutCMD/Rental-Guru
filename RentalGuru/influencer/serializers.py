from django.db.models import Sum, Q
from django.utils.timezone import now
from rest_framework import serializers

from chat.models import Trip, RequestRent
from influencer.models import Influencer, ReferralLink, InfluencerRequest, QRCode, Contact, BankDetails, Organization, \
    InfluencerDocuments, PromoCode, RegistrationSource
from notification.models import Notification
from payment.models import Payment
from vehicle.models import Vehicle


class InfluencerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    date_of_birth = serializers.DateField(source='user.date_of_birth')
    avatar = serializers.ImageField(source='user.avatar', required=False)
    telephone = serializers.CharField(source='user.telephone')

    class Meta:
        model = Influencer
        fields = ['id', 'email', 'first_name', 'last_name', 'referral_code', 'user_id', 'date_of_birth', 'avatar', 'telephone']
        read_only_fields = ['id', 'referral_code', 'email']

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        user_data = validated_data.pop('user')
        email = user_data.get('email')
        first_name = user_data.get('first_name')
        last_name = user_data.get('last_name')

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "Пользователь с таким email уже зарегистрирован."})

        password = User.objects.make_random_password()

        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            role='member',
        )

        influencer = Influencer.objects.create(user=user, **validated_data)

        Notification.objects.create(
            user=user,
            content=f"Добро пожаловать, {first_name}! Вы успешно зарегистрированы как партнер. Ваш пароль: {password}",
        )

        return influencer


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLink
        fields = ['channel', 'link', 'count']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'contact_type', 'value', 'is_primary']


class BankDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankDetails
        fields = ['id', 'inn', 'ogrn', 'registration_date', 'account_number', 'account_owner']


class OrganizationSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True)
    bank_details = BankDetailsSerializer()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'country', 'city', 'address', 'contacts', 'bank_details']


class InfluencerDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerDocuments
        fields = ['number', 'photo', 'status']


class InfluencerDetailSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    date_of_birth = serializers.DateField(source='user.date_of_birth')
    avatar = serializers.ImageField(source='user.avatar', required=False)
    email = serializers.EmailField(source='user.email', read_only=True)
    telephone = serializers.CharField(source='user.telephone')
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    organization = OrganizationSerializer()
    document = InfluencerDocumentsSerializer(required=False, allow_null=True)
    referral_links = LinkSerializer(many=True, read_only=True)
    total_clicks = serializers.SerializerMethodField()
    total_rent_income = serializers.SerializerMethodField()

    class Meta:
        model = Influencer
        fields = ['id', 'user_id', 'first_name', 'last_name', 'referral_code', 'referral_links', 'total_clicks',
                  'total_rent_income', 'organization', 'document', 'date_of_birth', 'avatar', 'email', 'telephone']
        read_only_fields = ['referral_code', 'total_clicks', 'total_rent_income', 'email']

    def get_total_clicks(self, obj):
        return obj.referral_links.aggregate(total_count=Sum('count'))['total_count'] or 0

    def get_total_rent_income(self, obj):
        renter_users = obj.renters.values_list('user_id', flat=True)
        total_income = Trip.objects.filter(organizer_id__in=renter_users, status='finished').aggregate(total_cost=Sum('total_cost'))
        return total_income['total_cost'] or 0.00

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        self.update_user(instance.user, user_data)

        organization_data = validated_data.pop('organization', None)
        if organization_data:
            self.update_organization(instance, organization_data)

        document_data = validated_data.pop('document', None)
        if document_data:
            self.update_document(instance, document_data)

        instance.save()
        return instance

    def update_user(self, user, user_data):
        """Обновление данных пользователя."""
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        if 'date_of_birth' in user_data:
            user.date_of_birth = user_data['date_of_birth']
        if 'telephone' in user_data:
            user.telephone = user_data['telephone']
        user.save()

    def update_organization(self, instance, organization_data):
        """Обновление или создание организации и связанных объектов."""
        organization = instance.organization
        if not organization:
            contacts_data = organization_data.pop('contacts', [])
            bank_details_data = organization_data.pop('bank_details', None)
            organization = Organization.objects.create(**organization_data)
            instance.organization = organization
            self.update_contacts(organization, contacts_data)
            if bank_details_data:
                self.update_bank_details(organization, bank_details_data)
        else:
            contacts_data = organization_data.pop('contacts', [])
            bank_details_data = organization_data.pop('bank_details', None)
            for attr, value in organization_data.items():
                setattr(organization, attr, value)
            organization.save()

            self.update_contacts(organization, contacts_data)
            if bank_details_data:
                self.update_bank_details(organization, bank_details_data)

    def update_contacts(self, organization, contacts_data):
        """Обновление контактов организации."""
        if contacts_data is not None:
            contact_ids = []
            for contact_data in contacts_data:
                contact, _ = Contact.objects.update_or_create(
                    organization=organization,
                    contact_type=contact_data['contact_type'],
                    defaults=contact_data
                )
                contact_ids.append(contact.id)
            organization.contacts.set(contact_ids)
        else:
            organization.contacts.clear()

    def update_bank_details(self, organization, bank_details_data):
        """Обновление или создание банковских данных."""
        if organization.bank_details:
            for attr, value in bank_details_data.items():
                setattr(organization.bank_details, attr, value)
            organization.bank_details.save()
        else:
            bank_details = BankDetails.objects.create(**bank_details_data)
            organization.bank_details = bank_details
            organization.save()

    def update_document(self, instance, document_data):
        """Обновление документа инфлюенсера."""
        request = self.context.get('request')
        user_role = getattr(request.user, 'role', None) if request else None

        if document_data.get('status') != 'pending' and user_role not in ['admin', 'manager']:
            document_data['status'] = 'pending'

        if hasattr(instance, 'document') and instance.document:
            for attr, value in document_data.items():
                setattr(instance.document, attr, value)
            instance.document.save()
        else:
            document_data['influencer'] = instance
            document = InfluencerDocuments.objects.create(**document_data)
            instance.document = document


class InfluencerRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerRequest
        fields = ['name', 'city', 'telephone', 'email', 'social', 'description']


class InfluencerRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerRequest
        fields = ['id', 'name', 'city', 'telephone', 'email', 'social', 'description', 'created_at']


class ReferralLinkSerializer(serializers.ModelSerializer):
    influencer_id = serializers.IntegerField(source='influencer.id', read_only=True)
    influencer_name = serializers.CharField(source='influencer.user.first_name', read_only=True)
    turnover = serializers.SerializerMethodField()
    income = serializers.SerializerMethodField()

    class Meta:
        model = ReferralLink
        fields = ['id', 'influencer_id', 'influencer_name', 'channel', 'link', 'count', 'income', 'turnover', 'created_at']
        read_only_fields = ['id', 'influencer_id', 'influencer_name', 'link', 'count', 'income', 'turnover', 'created_at']

    def create(self, validated_data):
        validated_data['influencer'] = self.context['request'].user.influencer
        referral_link = ReferralLink.objects.create(**validated_data)
        return referral_link

    def get_turnover(self, obj):
        """
        Подсчет суммы успешных платежей для ссылок инфлюенсера.
        """
        registered_users = RegistrationSource.objects.filter(
            source_type='qr_code',
            source_details=obj.link
        ).values_list('user', flat=True)
        organizer_rents = RequestRent.objects.filter(
            organizer__in=registered_users
        )

        lessor_rents = RequestRent.objects.filter(
            content_type__model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic'],
            object_id__in=Vehicle.objects.filter(
                owner__in=registered_users
            ).values_list('id', flat=True)
        )

        all_rents = organizer_rents | lessor_rents

        turnover = Payment.objects.filter(
            request_rent__in=all_rents,
            status='success'
        ).aggregate(total_sum=Sum('amount'))['total_sum'] or 0

        return turnover

    def get_income(self, obj):
        """
        Подсчет дохода инфлюенсера на основе оборота и комиссии.
        """
        turnover = self.get_turnover(obj)
        commission = getattr(obj.influencer, 'commission', 0)
        return (turnover * commission) / 100


class QRCodeSerializer(serializers.ModelSerializer):
    influencer_name = serializers.CharField(source='influencer.user.first_name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()
    turnover = serializers.SerializerMethodField()
    income = serializers.SerializerMethodField()

    class Meta:
        model = QRCode
        fields = [
            'id',
            'influencer',
            'influencer_name',
            'channel',
            'referral_link',
            'qr_code_url',
            'created_at',
            'count',
            'turnover',
            'income'
        ]
        read_only_fields = ['referral_link', 'qr_code_url', 'created_at', 'influencer', 'count', 'turnover', 'income', 'created_at']

    def get_qr_code_url(self, obj):
        """Возвращает полный URL к QR-коду."""
        request = self.context.get('request')
        if obj.qr_code_image:
            return request.build_absolute_uri(obj.qr_code_image.url) if request else obj.qr_code_image.url
        return None

    def get_turnover(self, obj):
        """
        Подсчет суммы успешных платежей для QR-кода инфлюенсера.
        """
        # request_rents = RequestRent.objects.filter(
        #     Q(organizer__renter__influencer=obj.influencer) |
        #     Q(content_type__model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic'],
        #       object_id__in=Vehicle.objects.filter(
        #           owner__renter__influencer=obj.influencer
        #       ).values_list('id', flat=True))
        # ).distinct()
        #
        # turnover = Payment.objects.filter(
        #     request_rent__in=request_rents,
        #     status='success'
        # ).aggregate(total_sum=Sum('amount'))['total_sum'] or 0
        #
        # return turnover

        registered_users = RegistrationSource.objects.filter(
            source_type='qr_code',
            source_details=obj.referral_link
        ).values_list('user', flat=True)
        organizer_rents = RequestRent.objects.filter(
            organizer__in=registered_users
        )

        lessor_rents = RequestRent.objects.filter(
            content_type__model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic'],
            object_id__in=Vehicle.objects.filter(
                owner__in=registered_users
            ).values_list('id', flat=True)
        )

        all_rents = organizer_rents | lessor_rents

        turnover = Payment.objects.filter(
            request_rent__in=all_rents,
            status='success'
        ).aggregate(total_sum=Sum('amount'))['total_sum'] or 0

        return turnover

    def get_income(self, obj):
        """
        Подсчет дохода инфлюенсера на основе оборота и комиссии.
        """
        turnover = self.get_turnover(obj)
        commission = getattr(obj.influencer, 'commission', 0)
        return (turnover * commission) / 100


class PromoCodeSerializer(serializers.ModelSerializer):
    turnover = serializers.SerializerMethodField()
    income = serializers.SerializerMethodField()

    class Meta:
        model = PromoCode
        fields = '__all__'
        read_only_fields = ['count', 'turnover', 'income', 'created_at']

    def validate(self, attrs):
        promo_type = attrs.get('type')
        total = attrs.get('total', 0)
        expiration_date = attrs.get('expiration_date')

        if not promo_type:
            raise serializers.ValidationError(
                'Поле "Тип промокода" обязательно для заполнения.'
            )

        if promo_type == PromoCode.TYPE_PERCENT and total > 50:
            raise serializers.ValidationError(
                'Если выбран тип "Процент", "Количество" не может превышать 50.'
            )

        if expiration_date and expiration_date < now():
            raise serializers.ValidationError(
                'Срок действия промокода не может быть в прошлом.'
            )

        return attrs

    def get_turnover(self, obj):
        """
        Подсчет суммы успешных платежей для промокода.
        """
        if not obj.influencer:
            return 0

        registered_users = RegistrationSource.objects.filter(
            source_type='promo',
            source_details=obj.title
        ).values_list('user', flat=True)

        organizer_rents = RequestRent.objects.filter(
            organizer__in=registered_users
        )

        lessor_rents = RequestRent.objects.filter(
            content_type__model__in=['auto', 'bike', 'ship', 'helicopter', 'specialtechnic'],
            object_id__in=Vehicle.objects.filter(
                owner__in=registered_users
            ).values_list('id', flat=True)
        )

        all_rents = organizer_rents | lessor_rents

        turnover = Payment.objects.filter(
            request_rent__in=all_rents,
            status='success'
        ).aggregate(total_sum=Sum('amount'))['total_sum'] or 0

        return turnover

    def get_income(self, obj):
        """
        Подсчет дохода инфлюенсера на основе оборота и комиссии.
        """
        if not obj.influencer:
            return 0

        turnover = self.get_turnover(obj)
        commission = getattr(obj.influencer, 'commission', 0)
        return (turnover * commission) / 100


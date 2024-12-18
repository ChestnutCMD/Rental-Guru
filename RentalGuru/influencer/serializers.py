from django.db.models import Sum
from rest_framework import serializers

from chat.models import Trip
from influencer.models import Influencer, ReferralLink, InfluencerRequest, QRCode, Contact, BankDetails, Organization, \
    InfluencerDocuments
from notification.models import Notification


class InfluencerSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = Influencer
        fields = ['id', 'email', 'first_name', 'last_name', 'referral_code', 'user_id']
        read_only_fields = ['id', 'referral_code']

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


class ReferralLinkSerializer(serializers.ModelSerializer):
    influencer_id = serializers.IntegerField(source='influencer.id', read_only=True)
    influencer_name = serializers.CharField(source='influencer.user.first_name', read_only=True)

    class Meta:
        model = ReferralLink
        fields = ['id', 'influencer_id', 'influencer_name', 'channel', 'link', 'count']
        read_only_fields = ['id', 'influencer_id', 'influencer_name', 'link', 'count']

    def create(self, validated_data):
        validated_data['influencer'] = self.context['request'].user.influencer
        referral_link = ReferralLink.objects.create(**validated_data)
        return referral_link


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
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    organization = OrganizationSerializer()
    document = InfluencerDocumentsSerializer(required=False, allow_null=True)
    referral_links = LinkSerializer(many=True, read_only=True)
    total_clicks = serializers.SerializerMethodField()
    total_rent_income = serializers.SerializerMethodField()

    class Meta:
        model = Influencer
        fields = ['id', 'user_id', 'first_name', 'last_name', 'referral_code', 'referral_links', 'total_clicks', 'total_rent_income', 'organization', 'document']
        read_only_fields = ['referral_code', 'total_clicks', 'total_rent_income',]

    def get_total_clicks(self, obj):
        return obj.referral_links.aggregate(total_count=Sum('count'))['total_count'] or 0

    def get_total_rent_income(self, obj):
        renter_users = obj.renters.values_list('user_id', flat=True)
        total_income = Trip.objects.filter(organizer_id__in=renter_users, status='finished').aggregate(total_cost=Sum('total_cost'))
        return total_income['total_cost'] or 0.00

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user_role = getattr(request.user, 'role', None) if request else None

        user_data = validated_data.pop('user', {})
        user = instance.user
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        user.save()

        organization_data = validated_data.pop('organization', None)
        if organization_data:
            organization = instance.organization
            if not organization:
                organization = Organization.objects.create(**organization_data)
                instance.organization = organization
            else:
                contacts_data = organization_data.pop('contacts', [])
                bank_details_data = organization_data.pop('bank_details', {})
                for attr, value in organization_data.items():
                    setattr(organization, attr, value)
                organization.save()
                if contacts_data is not None:
                    contact_ids = []
                    for contact_data in contacts_data:
                        contact, _ = Contact.objects.get_or_create(**contact_data)
                        contact_ids.append(contact.id)
                    organization.contacts.set(contact_ids)
                else:
                    organization.contacts.clear()
                if bank_details_data:
                    bank_details, _ = BankDetails.objects.update_or_create(
                        id=organization.bank_details.id if organization.bank_details else None,
                        defaults=bank_details_data
                    )
                    organization.bank_details = bank_details
                    organization.save()

        document_data = validated_data.pop('document', None)
        if document_data:
            if document_data.get('status') != 'pending':
                if user_role not in ['admin', 'manager']:
                    document_data['status'] = 'pending'
            if hasattr(instance, 'document') and instance.document:
                for attr, value in document_data.items():
                    setattr(instance.document, attr, value)
                instance.document.save()
            else:
                document_data['influencer'] = instance
                document = InfluencerDocuments.objects.create(**document_data)
                instance.document = document

        instance.save()
        return instance


class InfluencerRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerRequest
        fields = ['name', 'city', 'telephone', 'email', 'social', 'description']


class InfluencerRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfluencerRequest
        fields = ['id', 'name', 'city', 'telephone', 'email', 'social', 'description', 'created_at']


class QRCodeSerializer(serializers.ModelSerializer):
    influencer_name = serializers.CharField(source='influencer.user.first_name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = QRCode
        fields = [
            'id',
            'influencer',
            'influencer_name',
            'channel',
            'referral_link',
            'qr_code_url',
            'created_at'
        ]
        read_only_fields = ['referral_link', 'qr_code_url', 'created_at', 'influencer']

    def get_qr_code_url(self, obj):
        """Возвращает полный URL к QR-коду."""
        request = self.context.get('request')
        if obj.qr_code_image:
            return request.build_absolute_uri(obj.qr_code_image.url) if request else obj.qr_code_image.url
        return None

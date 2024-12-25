from django.contrib import admin
from django.utils.html import format_html

from influencer.models import Influencer, ReferralLink, BankDetails, Contact, Organization, InfluencerDocuments, QRCode, \
    PromoCode


class ReferralLinkInline(admin.TabularInline):
    model = ReferralLink
    extra = 1
    readonly_fields = ('count', 'created_at')
    verbose_name = "Реферальная ссылка"
    verbose_name_plural = "Реферальные ссылки"

class QRCodeInline(admin.TabularInline):
    model = QRCode
    extra = 1
    readonly_fields = ('qr_code_image_preview', 'count', 'created_at')
    fields = ('channel', 'referral_link', 'qr_code_image_preview', 'count', 'created_at')
    verbose_name = "QR-код"
    verbose_name_plural = "QR-коды"

    def qr_code_image_preview(self, obj):
        if obj.qr_code_image:
            return format_html('<img src="{}" width="100" height="100" />', obj.qr_code_image.url)
        return "QR-код не создан"
    qr_code_image_preview.short_description = "Предпросмотр QR-кода"

class InfluencerDocumentsInline(admin.StackedInline):
    model = InfluencerDocuments
    can_delete = False
    verbose_name = "Документы"
    verbose_name_plural = "Документы"

@admin.register(Influencer)
class InfluencerAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code', 'commission', 'get_organization')
    list_filter = ('commission',)
    search_fields = ('user__username', 'user__email', 'referral_code')
    readonly_fields = (
        'referral_code',
        'org_name', 'org_country', 'org_city', 'org_address',
        'bank_inn', 'bank_ogrn', 'bank_account', 'bank_owner',
        'org_contacts'
    )

    inlines = [
        InfluencerDocumentsInline,
        ReferralLinkInline,
        QRCodeInline,
    ]

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'referral_code', 'commission', 'organization')
        }),
        ('Информация об организации', {
            'classes': ('collapse',),
            'fields': ('org_name', 'org_country', 'org_city', 'org_address', 'org_contacts'),
        }),
        ('Банковские реквизиты', {
            'classes': ('collapse',),
            'fields': ('bank_inn', 'bank_ogrn', 'bank_account', 'bank_owner'),
        }),
    )

    def get_organization(self, obj):
        return obj.organization.name if obj.organization else '-'
    get_organization.short_description = 'Организация'

    def org_name(self, obj):
        return obj.organization.name if obj.organization else '-'
    org_name.short_description = "Название организации"

    def org_country(self, obj):
        return obj.organization.country if obj.organization else '-'
    org_country.short_description = "Страна"

    def org_city(self, obj):
        return obj.organization.city if obj.organization else '-'
    org_city.short_description = "Город"

    def org_address(self, obj):
        return obj.organization.address if obj.organization else '-'
    org_address.short_description = "Адрес"

    def bank_inn(self, obj):
        return obj.organization.bank_details.inn if obj.organization and obj.organization.bank_details else '-'
    bank_inn.short_description = "ИНН"

    def bank_ogrn(self, obj):
        return obj.organization.bank_details.ogrn if obj.organization and obj.organization.bank_details else '-'
    bank_ogrn.short_description = "ОГРН"

    def bank_account(self, obj):
        return obj.organization.bank_details.account_number if obj.organization and obj.organization.bank_details else '-'
    bank_account.short_description = "Расчетный счет"

    def bank_owner(self, obj):
        return obj.organization.bank_details.account_owner if obj.organization and obj.organization.bank_details else '-'
    bank_owner.short_description = "Владелец счета"

    def org_contacts(self, obj):
        if not obj.organization or not obj.organization.contacts.exists():
            return '-'
        contacts = obj.organization.contacts.all()
        return format_html('<br>'.join([f"{c.get_contact_type_display()}: {c.value}" for c in contacts]))
    org_contacts.short_description = "Контакты"


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('title', 'influencer', 'type', 'total', 'expiration_date', 'count', 'created_at', )
    list_filter = ('type',)
    search_fields = ('name',)
    ordering = ('created_at',)
    readonly_fields = ('count',)


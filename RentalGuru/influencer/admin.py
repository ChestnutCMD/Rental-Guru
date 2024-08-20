from django.contrib import admin

from influencer.models import Influencer, ReferralLink


class InfluencerAdmin(admin.ModelAdmin):
    list_display = ('user', 'referral_code')
    list_filter = ('user',)
    search_fields = ('user', )
    readonly_fields = ('user', 'referral_code')


admin.site.register(Influencer, InfluencerAdmin)


class ReferralLinkAdmin(admin.ModelAdmin):
    list_display = ('influencer', 'channel', 'link', 'count')
    list_filter = ('influencer',)
    search_fields = ('influencer', )
    readonly_fields = ('influencer', 'link', 'count')


admin.site.register(ReferralLink, ReferralLinkAdmin)

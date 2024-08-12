from django.contrib import admin

from .forms import LessorForm
from .models import User, Lessor, Renter

class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'date_of_birth', 'telephone', 'currency', 'avatar')
    list_filter = ('role',)

class LessorAdmin(admin.ModelAdmin):
    list_display = ('user', 'super_host', 'count_trip', 'average_response_time')
    list_filter = ('user__role',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            user_fields = [
                'user_email', 'user_first_name', 'user_last_name', 'user_date_of_birth',
                'user_telephone', 'user_currency', 'user_avatar', 'user_about',
                'user_email_notification', 'user_push_notification'
            ]
            return user_fields + list(super().get_readonly_fields(request, obj))
        return super().get_readonly_fields(request, obj)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email пользователя'

    def user_first_name(self, obj):
        return obj.user.first_name
    user_first_name.short_description = 'Имя пользователя'

    def user_last_name(self, obj):
        return obj.user.last_name
    user_last_name.short_description = 'Фамилия пользователя'

    def user_date_of_birth(self, obj):
        return obj.user.date_of_birth
    user_date_of_birth.short_description = 'Дата рождения'

    def user_telephone(self, obj):
        return obj.user.telephone
    user_telephone.short_description = 'Телефон'

    def user_currency(self, obj):
        return obj.user.currency
    user_currency.short_description = 'Валюта'

    def user_avatar(self, obj):
        return obj.user.avatar
    user_avatar.short_description = 'Аватар'

    def user_about(self, obj):
        return obj.user.about
    user_about.short_description = 'О себе'

    def user_email_notification(self, obj):
        return obj.user.email_notification
    user_email_notification.short_description = 'Email уведомления'

    def user_push_notification(self, obj):
        return obj.user.push_notification
    user_push_notification.short_description = 'Push уведомления'

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Основная информация', {
                'fields': ('user', 'super_host', 'count_trip', 'average_response_time')
            }),
        ]
        if obj:
            fieldsets.append(('Информация о пользователе', {
                'fields': (
                    'user_avatar', 'user_email', 'user_first_name', 'user_last_name', 'user_date_of_birth',
                    'user_telephone', 'user_currency', 'user_about',
                    'user_email_notification', 'user_push_notification'
                ),
                'classes': ('collapse',)
            }))
        return fieldsets


class RenterAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'verification', 'get_average_rating',
        'user_email', 'user_first_name', 'user_last_name',
        'user_date_of_birth', 'user_telephone', 'user_currency',
        'user_avatar', 'user_about', 'user_email_notification',
        'user_push_notification'
    )
    list_filter = ('user__role',)
    search_fields = ('user__first_name', 'user__last_name', 'user__email')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            user_fields = [
                'user_email', 'user_first_name', 'user_last_name', 'user_date_of_birth',
                'user_telephone', 'user_currency', 'user_avatar', 'user_about',
                'user_email_notification', 'user_push_notification'
            ]
            return user_fields + list(super().get_readonly_fields(request, obj))
        return super().get_readonly_fields(request, obj)

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Email пользователя'

    def user_first_name(self, obj):
        return obj.user.first_name
    user_first_name.short_description = 'Имя пользователя'

    def user_last_name(self, obj):
        return obj.user.last_name
    user_last_name.short_description = 'Фамилия пользователя'

    def user_date_of_birth(self, obj):
        return obj.user.date_of_birth
    user_date_of_birth.short_description = 'Дата рождения'

    def user_telephone(self, obj):
        return obj.user.telephone
    user_telephone.short_description = 'Телефон'

    def user_currency(self, obj):
        return obj.user.currency
    user_currency.short_description = 'Валюта'

    def user_avatar(self, obj):
        return obj.user.avatar
    user_avatar.short_description = 'Аватар'

    def user_about(self, obj):
        return obj.user.about
    user_about.short_description = 'О себе'

    def user_email_notification(self, obj):
        return obj.user.email_notification
    user_email_notification.short_description = 'Email уведомления'

    def user_push_notification(self, obj):
        return obj.user.push_notification
    user_push_notification.short_description = 'Push уведомления'

    def get_fieldsets(self, request, obj=None):
        fieldsets = [
            ('Основная информация', {
                'fields': ('user', 'verification', 'rating')
            }),
        ]
        if obj:
            fieldsets.append(('Информация о пользователе', {
                'fields': (
                    'user_email', 'user_first_name', 'user_last_name', 'user_date_of_birth',
                    'user_telephone', 'user_currency', 'user_avatar', 'user_about',
                    'user_email_notification', 'user_push_notification'
                ),
                'classes': ('collapse',)
            }))
        return fieldsets


admin.site.register(User, UserAdmin)
admin.site.register(Lessor, LessorAdmin)
admin.site.register(Renter, RenterAdmin)

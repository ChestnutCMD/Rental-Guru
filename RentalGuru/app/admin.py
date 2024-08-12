from django.contrib import admin

from app.models import User, Renter, Lessor


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    display = ('avatar',
               'first_name',
               'last_name',
               'role',
               'date_of_birth',
               'email',
               'telephone',
               'currency',
               'about',
               'email_notification',
               'push_notification',
               )
    search_fields = ('first_name',)
    ordering = ('first_name',)


@admin.register(Renter)
class RenterAdmin(admin.ModelAdmin):
    display = ('push_notification', 'user', 'favorite', 'verification', 'rating')


@admin.register(Lessor)
class RenterAdmin(admin.ModelAdmin):
    display = ('super_host', 'count_trip', 'average_response_time')

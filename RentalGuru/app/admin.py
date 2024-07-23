from django.contrib import admin

from app.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    display = '__all__'
    search_fields = ('first_name',)
    ordering = ('first_name',)

from django.contrib import admin
from .models import RequestRent, Chat, Message, ChatSupport, MessageSupport


@admin.register(RequestRent)
class RequestRentAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'organizer', 'start_date', 'end_date', 'vehicle')
    search_fields = ('organizer__first_name', 'status')
    list_filter = ('status', 'start_date', 'end_date')
    list_display_links = ('organizer', 'vehicle')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'request_rent', 'participants_list')
    search_fields = ('request_rent__organizer__first_name', 'participants__first_name')
    inlines = [MessageInline]
    list_display_links = ('participants_list', 'request_rent')

    def participants_list(self, obj):
        return ", ".join([p.first_name for p in obj.participants.all()])


class MessageSupportInline(admin.TabularInline):
    model = MessageSupport
    extra = 0


@admin.register(ChatSupport)
class ChatSupportAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator')
    search_fields = ('creator__first_name',)
    inlines = [MessageSupportInline]

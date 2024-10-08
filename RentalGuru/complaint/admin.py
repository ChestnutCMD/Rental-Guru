from django.contrib import admin
from tornado.escape import linkify

from complaint.models import Complaint


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_filter = ['topic', 'vehicle']
    list_display = ['id', linkify('user'), linkify('vehicle'), 'topic', 'description']

from django.contrib import admin
from .models import Franchise


@admin.register(Franchise)
class FranchiseAdmin(admin.ModelAdmin):
    list_display = ['name', 'unn', 'director']
    search_fields = ['name', 'unn', 'director']
    list_filter = ['country', 'city']

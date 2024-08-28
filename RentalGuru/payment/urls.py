from django.urls import path
from .views import tinkoff_webhook

urlpatterns = [
    path('webhook/tinkoff/', tinkoff_webhook, name='tinkoff_webhook'),
]
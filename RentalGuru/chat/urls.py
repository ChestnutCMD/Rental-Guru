# chat/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, ChatViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'trips', TripViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

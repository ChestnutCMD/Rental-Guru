from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, ChatViewSet, MessageViewSet, RequestRentViewSet, TopicSupportViewSet, \
    ChatSupportViewSet, MessageSupportViewSet

router = DefaultRouter()
router.register(r'request_rents', RequestRentViewSet, basename='request')
router.register(r'trips', TripViewSet, basename='trip')
router.register(r'chat', ChatViewSet, basename='chat')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'topics', TopicSupportViewSet, basename='topic')
router.register(r'support_chat', ChatSupportViewSet, basename='support')
router.register(r'support_messages', MessageSupportViewSet, basename='support_message')

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, ChatViewSet, MessageViewSet, check_redis, RequestRentViewSet, TopicSupportViewSet, \
    ChatSupportViewSet, MessageSupportViewSet

router = DefaultRouter()
router.register(r'request_rents', RequestRentViewSet)
router.register(r'trips', TripViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'topics', TopicSupportViewSet)
router.register(r'support_chat', ChatSupportViewSet)
router.register(r'support_messages', MessageSupportViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-redis/', check_redis),
]

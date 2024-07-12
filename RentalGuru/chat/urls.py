from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TripViewSet, ChatViewSet, MessageViewSet, check_redis, RequestRentViewSet

router = DefaultRouter()
router.register(r'request_rents', RequestRentViewSet)
router.register(r'trips', TripViewSet)
router.register(r'chats', ChatViewSet)
router.register(r'messages', MessageViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-redis/', check_redis),
]

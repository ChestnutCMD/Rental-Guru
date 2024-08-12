from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VehicleParkViewSet, RequestsByParkView, ChatsByParkView

router = DefaultRouter()
router.register(r'vehicle_park', VehicleParkViewSet, basename='vehicle_park')

urlpatterns = [
    path('vehicle_park/<int:park_id>/chats/', ChatsByParkView.as_view(), name='chats-by-park'),
    path('vehicle_park/<int:park_id>/requests/', RequestsByParkView.as_view(), name='requests-by-park'),
    path('', include(router.urls))
]

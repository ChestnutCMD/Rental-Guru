from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VehicleParkViewSet, RequestsByParkView, ChatsByParkView, FranchiseViewSet, RequestsByFranchiseView, \
    ChatsByFranchiseView

router = DefaultRouter()
router.register(r'vehicle_park', VehicleParkViewSet, basename='vehicle_park')
router.register(r'', FranchiseViewSet, basename='franchise')

urlpatterns = [
    path('<int:franchise_id>/requests/', RequestsByFranchiseView.as_view(), name='requests-by-franchise'),
    path('<int:franchise_id>/chats/', ChatsByFranchiseView.as_view(), name='chats-by-franchise'),
    path('vehicle_park/<int:park_id>/chats/', ChatsByParkView.as_view(), name='chats-by-park'),
    path('vehicle_park/<int:park_id>/requests/', RequestsByParkView.as_view(), name='requests-by-park'),
    path('', include(router.urls))
]

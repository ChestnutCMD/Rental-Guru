from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import VehicleParkViewSet, RequestsByParkView, ChatsByParkView, FranchiseViewSet, RequestsByFranchiseView, \
    ChatsByFranchiseView, LessorsByFranchiseView, VehiclesByFranchiseView, franchise_statistics, \
    vehicle_park_statistics, RequestFranchiseCreateView, RequestFranchiseListView, RequestFranchiseDeleteView

router = DefaultRouter()
router.register(r'vehicle_park', VehicleParkViewSet, basename='vehicle_park')
router.register(r'', FranchiseViewSet, basename='franchise')

urlpatterns = [
    path('vehicle_park/<int:park_id>/chats/', ChatsByParkView.as_view(), name='chats-by-park'),
    path('vehicle_park/<int:park_id>/requests/', RequestsByParkView.as_view(), name='requests-by-park'),
    path('vehicle-park/<int:vehicle_park_id>/statistics/', vehicle_park_statistics, name='vehicle-park-statistics'),

    path('<int:franchise_id>/statistics/', franchise_statistics, name='franchise-statistics'),
    path('<int:franchise_id>/requests/', RequestsByFranchiseView.as_view(), name='requests-by-franchise'),
    path('<int:franchise_id>/chats/', ChatsByFranchiseView.as_view(), name='chats-by-franchise'),
    path('franchises/<int:franchise_id>/lessors/', LessorsByFranchiseView.as_view(), name='lessors-by-franchise'),
    path('franchises/<int:franchise_id>/vehicles/', VehiclesByFranchiseView.as_view(), name='vehicles-by-franchise'),

    path('', include(router.urls)),

    path('request-franchise/create/', RequestFranchiseCreateView.as_view(), name='request-franchise-create'),
    path('request-franchise/', RequestFranchiseListView.as_view(), name='request-franchise-list'),
    path('request-franchise/delete/<int:pk>/', RequestFranchiseDeleteView.as_view(), name='request-franchise-delete'),
]

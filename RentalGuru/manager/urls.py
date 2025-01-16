from django.urls import path, include
from rest_framework.routers import DefaultRouter

from influencer.views import RequestWithdrawViewSet
from manager.views import ManagerPermissionViewSet, ManagerViewSet, AvailableModelsView

router = DefaultRouter()
router.register(r'permissions_for_managers', ManagerPermissionViewSet, basename='permissions_for_managers')
router.register(r'managers', ManagerViewSet, basename='managers')
router.register(r'request_withdraw', RequestWithdrawViewSet, basename='request_withdraw')

urlpatterns = [
    path('permission_models', AvailableModelsView.as_view(), name='permission_models'),
    path('', include(router.urls))
]

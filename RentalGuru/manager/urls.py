from django.urls import path, include
from rest_framework.routers import DefaultRouter

from manager.views import ManagerPermissionViewSet, ManagerViewSet, AvailableModelsView

router = DefaultRouter()
router.register(r'permissions_for_managers', ManagerPermissionViewSet)
router.register(r'managers', ManagerViewSet)

urlpatterns = [
    path('permission_models', AvailableModelsView.as_view(), name='permission_models'),
    path('', include(router.urls))
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import ChangePasswordView, UserViewSet, RenterDocumentsViewSet, FavoriteVehicleViewSet, UpdateRatingView, \
    CustomTokenObtainPairView, get_fcm_token

from rest_framework_simplejwt.views import TokenRefreshView


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'renter-documents', RenterDocumentsViewSet, basename='renter-documents')
router.register(r'favorites', FavoriteVehicleViewSet, basename='favorite-vehicle')

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('renter/<int:renter_id>/update_rating/', UpdateRatingView.as_view(), name='update_rating'),
    path('fcm_token/', get_fcm_token, name='fcm_token'),
    path('', include(router.urls))
]

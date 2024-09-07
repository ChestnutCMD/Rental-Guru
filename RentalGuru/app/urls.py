from django.urls import path, include
from rest_framework.routers import DefaultRouter


from .views import ChangePasswordView, UserViewSet, RenterDocumentsViewSet, FavoriteVehicleViewSet, UpdateRatingView, \
    CustomTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmView, SocialLoginView, FavoriteListViewSet

from rest_framework_simplejwt.views import TokenRefreshView


router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'renter-documents', RenterDocumentsViewSet, basename='renter-documents')
router.register(r'favorites', FavoriteVehicleViewSet, basename='favorite-vehicle')
router.register(r'favorite-lists', FavoriteListViewSet, basename='favorite-list')

urlpatterns = [
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('renter/<int:renter_id>/update_rating/', UpdateRatingView.as_view(), name='update_rating'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('auth/social/', SocialLoginView.as_view(), name='social-login'),
    path('', include(router.urls))
]

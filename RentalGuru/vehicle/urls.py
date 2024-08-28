from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VehicleBrandViewSet, VehicleModelViewSet, AutoViewSet, BikeViewSet, ShipViewSet, HelicopterViewSet, \
    SpecialTechnicViewSet, UpdateRatingView, gps_tracking_view

router = DefaultRouter()
router.register(r'brands', VehicleBrandViewSet)
router.register(r'models', VehicleModelViewSet)
router.register(r'autos', AutoViewSet)
router.register(r'bikes', BikeViewSet)
router.register(r'ships', ShipViewSet)
router.register(r'helicopters', HelicopterViewSet)
router.register(r'special-technics', SpecialTechnicViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('update-rating/', UpdateRatingView.as_view(), name='update-rating'),
    path('ws/gps_tracking/<int:vehicle_id>/', gps_tracking_view, name='gps_tracking'),
]

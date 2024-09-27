from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import VehicleBrandViewSet, VehicleModelViewSet, AutoViewSet, BikeViewSet, ShipViewSet, HelicopterViewSet, \
    SpecialTechnicViewSet, UpdateRatingView, gps_tracking_view, VehicleFeaturesFunctionsListView, \
    AutoFeaturesAdditionallyListView, BikeFeaturesAdditionallyListView, ShipFeaturesAdditionallyListView, \
    FeaturesForChildrenListView, FeaturesEquipmentListView, PaymentMethodListView, BikeTransmissionListView, \
    AutoTransmissionListView, AutoFuelTypeListView, AutoBodyTypeListView, VehicleClassListView

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
    path('vehicle_features/', VehicleFeaturesFunctionsListView.as_view(), name='vehicle_features'),
    path('auto_features/', AutoFeaturesAdditionallyListView.as_view(), name='auto_features'),
    path('bike_features/', BikeFeaturesAdditionallyListView.as_view(), name='bike_features'),
    path('ship_features/', ShipFeaturesAdditionallyListView.as_view(), name='ship_features'),
    path('auto_for_children/', FeaturesForChildrenListView.as_view(), name='for_children_features'),
    path('ship_equipment/', FeaturesEquipmentListView.as_view(), name='equipment_features'),
    path('payment_method/', PaymentMethodListView.as_view(), name='payment_method'),

    path('bike_transmission/', BikeTransmissionListView.as_view(), name='bike_transmission'),
    path('auto_fuel_type/', AutoFuelTypeListView.as_view(), name='auto_fuel_type'),
    path('auto_transmission/', AutoTransmissionListView.as_view(), name='auto_transmission'),
    path('auto_body_type/', AutoBodyTypeListView.as_view(), name='auto_body_type'),
    path('vehicle_class/', VehicleClassListView.as_view(), name='vehicle_class'),

    path('ws/gps_tracking/<int:vehicle_id>/', gps_tracking_view, name='gps_tracking'),
]

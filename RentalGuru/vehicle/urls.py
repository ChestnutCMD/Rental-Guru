from django.urls import path
from . import views

urlpatterns = [
    path('types/', views.VehicleTypeListCreateAPIView.as_view(), name='vehicle-type-list-create'),
    path('types/<int:pk>/', views.VehicleTypeDetailAPIView.as_view(), name='vehicle-type-detail'),

    path('brands/', views.VehicleBrandListCreateAPIView.as_view(), name='vehicle-brand-list-create'),
    path('brands/<int:pk>/', views.VehicleBrandDetailAPIView.as_view(), name='vehicle-brand-detail'),

    path('models/', views.VehicleModelListCreateAPIView.as_view(), name='vehicle-model-list-create'),
    path('models/<int:pk>/', views.VehicleModelDetailAPIView.as_view(), name='vehicle-model-detail'),

    path('', views.VehicleListCreateAPIView.as_view(), name='vehicle-list-create'),
    path('<int:pk>/', views.VehicleDetailAPIView.as_view(), name='vehicle-detail'),
]


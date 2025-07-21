from django.urls import path
from .views import TripByCityView

urlpatterns = [
    path('', TripByCityView.as_view(), name='journal'),
]

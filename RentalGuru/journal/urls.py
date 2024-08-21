from django.urls import path
from .views import TripByFranchiseView

urlpatterns = [
    path('<int:franchise_id>/', TripByFranchiseView.as_view(), name='journal'),
]

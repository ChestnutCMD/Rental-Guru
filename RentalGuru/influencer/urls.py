from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReferralLinkViewSet, InfluencerListCreateView, InfluencerRetrieveDestroyView

router = DefaultRouter()
router.register(r'referral-links', ReferralLinkViewSet)

urlpatterns = [
    path('', InfluencerListCreateView.as_view(), name='influencer-list-create'),
    path('<int:pk>/', InfluencerRetrieveDestroyView.as_view(), name='influencer-retrieve-destroy'),
    path('', include(router.urls)),
]

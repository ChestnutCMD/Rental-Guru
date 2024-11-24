from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReferralLinkViewSet, InfluencerListCreateView, InfluencerRetrieveDestroyView, \
    InfluencerRequestCreateView, InfluencerRequestListView, InfluencerRequestDeleteView

router = DefaultRouter()
router.register(r'referral-links', ReferralLinkViewSet)

urlpatterns = [
    path('', InfluencerListCreateView.as_view(), name='influencer-list-create'),
    path('<int:pk>/', InfluencerRetrieveDestroyView.as_view(), name='influencer-retrieve-destroy'),
    path('influencer_requests/', InfluencerRequestCreateView.as_view(), name='influencer-request-create'),
    path('influencer_requests/list/', InfluencerRequestListView.as_view(), name='influencer-request-list'),
    path('influencer_requests/delete/<int:pk>/', InfluencerRequestDeleteView.as_view(), name='influencer-request-delete'),
    path('', include(router.urls)),
]

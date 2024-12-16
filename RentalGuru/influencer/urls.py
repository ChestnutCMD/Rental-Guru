from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReferralLinkViewSet, InfluencerRequestCreateView, InfluencerRequestListView, \
    InfluencerRequestDeleteView, InfluencerViewSet, QRCodeViewSet

router = DefaultRouter()
router.register(r'referral-links', ReferralLinkViewSet)
router.register('influencers', InfluencerViewSet)
router.register(r'qr-codes', QRCodeViewSet, basename='qr-code')


urlpatterns = [
    path('influencer_requests/', InfluencerRequestCreateView.as_view(), name='influencer-request-create'),
    path('influencer_requests/list/', InfluencerRequestListView.as_view(), name='influencer-request-list'),
    path('influencer_requests/delete/<int:pk>/', InfluencerRequestDeleteView.as_view(), name='influencer-request-delete'),
    path('', include(router.urls)),
]

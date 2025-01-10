from django.urls import path

from report.views import LessorReportView, InfluencerReportView, FranchiseReportView

urlpatterns = [
    path('lessor_report/', LessorReportView.as_view(), name='lessor_report'),
    path('influencer_report/', InfluencerReportView.as_view(), name='influencer_report'),
    path('franchise_report/', FranchiseReportView.as_view(), name='franchise_report'),
]

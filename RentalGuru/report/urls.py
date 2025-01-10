from django.urls import path

from report.views import LessorReportView, InfluencerReportView

urlpatterns = [
    path('lessor_report/', LessorReportView.as_view(), name='lessor-report'),
    path('influencer_report/', InfluencerReportView.as_view(), name='influencer-report')
]

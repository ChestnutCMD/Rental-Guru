from django.urls import path

from report.views import LessorReportView

urlpatterns = [
    path('lessor-report/', LessorReportView.as_view(), name='lessor-report'),
]

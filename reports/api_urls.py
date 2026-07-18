from django.urls import path
from . import api_views

urlpatterns = [
    path('reports/summary/', api_views.PersonalReportView.as_view(), name='api_personal_report'),
    path('reports/org-summary/', api_views.OrgReportView.as_view(), name='api_org_report'),
]

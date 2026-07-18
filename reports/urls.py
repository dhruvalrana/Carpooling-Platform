from django.urls import path
from . import views

urlpatterns = [
    path('', views.personal_reports, name='reports'),
    path('org/', views.org_reports, name='org_reports'),
    path('settings/', views.settings_hub, name='settings'),
]

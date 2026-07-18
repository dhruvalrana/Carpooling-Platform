from django.urls import path
from . import views

urlpatterns = [
    path('tracking/ping/', views.ping, name='api_tracking_ping'),
    path('tracking/<int:ride_id>/latest/', views.latest_ping, name='api_tracking_latest'),
]

"""Accounts REST API URLs."""
from django.urls import path
from . import api_views

urlpatterns = [
    path('auth/me/', api_views.MeView.as_view(), name='api_me'),
]

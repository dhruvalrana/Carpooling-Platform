from django.urls import path
from . import api_views

urlpatterns = [
    path('vehicles/', api_views.VehicleListCreateView.as_view(), name='api_vehicles'),
    path('vehicles/<int:pk>/', api_views.VehicleDetailView.as_view(), name='api_vehicle_detail'),
]

from django.urls import path
from . import api_views

urlpatterns = [
    path('rides/', api_views.RideListCreateView.as_view(), name='api_rides'),
    path('rides/search/', api_views.RideSearchView.as_view(), name='api_ride_search'),
    path('rides/<int:pk>/', api_views.RideDetailView.as_view(), name='api_ride_detail'),
    path('rides/<int:pk>/route-preview/', api_views.RoutePreviewView.as_view(), name='api_route_preview'),
]

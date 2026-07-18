from django.urls import path
from . import api_views

urlpatterns = [
    path('trips/', api_views.TripListCreateView.as_view(), name='api_trips'),
    path('trips/mine/', api_views.MyTripsView.as_view(), name='api_my_trips'),
    path('trips/<int:pk>/', api_views.TripDetailView.as_view(), name='api_trip_detail'),
    path('trips/<int:pk>/start/', api_views.TripStartView.as_view(), name='api_trip_start'),
    path('trips/<int:pk>/complete/', api_views.TripCompleteView.as_view(), name='api_trip_complete'),
    path('chat/<int:trip_pk>/messages/', api_views.ChatMessagesView.as_view(), name='api_chat_messages'),
]

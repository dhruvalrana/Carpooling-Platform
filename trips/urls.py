from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_trips, name='my_trips'),
    path('<int:pk>/', views.trip_detail, name='trip_detail'),
    path('book/<int:ride_pk>/', views.book_ride_view, name='book_ride'),
    path('<int:pk>/transition/', views.transition_trip, name='transition_trip'),
    path('<int:pk>/chat/', views.send_chat, name='send_chat'),
    path('history/', views.ride_history, name='ride_history'),
]

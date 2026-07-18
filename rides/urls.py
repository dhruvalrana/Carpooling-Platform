from django.urls import path
from . import views

urlpatterns = [
    path('offer/', views.offer_ride, name='offer_ride'),
    path('offer/confirm/', views.route_confirm_offer, name='route_confirm_offer'),
    path('find/', views.find_ride, name='find_ride'),
    path('<int:pk>/', views.ride_detail, name='ride_detail'),
    path('my/', views.my_offered_rides, name='my_offered_rides'),
]

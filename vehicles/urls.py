from django.urls import path
from . import views

urlpatterns = [
    path('', views.my_vehicles, name='my_vehicles'),
    path('add/', views.add_vehicle, name='add_vehicle'),
    path('<int:pk>/edit/', views.edit_vehicle, name='edit_vehicle'),
    path('<int:pk>/delete/', views.delete_vehicle, name='delete_vehicle'),
]

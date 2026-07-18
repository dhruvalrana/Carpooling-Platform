from django.urls import path
from . import views

urlpatterns = [
    path('<int:trip_pk>/', views.payment_screen, name='payment_screen'),
    path('<int:trip_pk>/pay/', views.process_payment, name='process_payment'),
    path('<int:trip_pk>/verify/', views.verify_payment, name='verify_payment'),
]

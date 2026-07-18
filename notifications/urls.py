from django.urls import path
from . import views

urlpatterns = [
    path('', views.notifications_list, name='notifications'),
    path('<int:pk>/read/', views.mark_read, name='mark_notification_read'),
]

from django.urls import path
from . import views

urlpatterns = [
    path('', views.wallet_view, name='wallet'),
    path('recharge/', views.initiate_recharge, name='wallet_recharge'),
]

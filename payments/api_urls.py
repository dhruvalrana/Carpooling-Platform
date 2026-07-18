from django.urls import path
from . import api_views

urlpatterns = [
    path('payments/<int:trip_pk>/create-order/', api_views.CreateOrderView.as_view(), name='api_create_order'),
    path('payments/<int:trip_pk>/verify/', api_views.VerifyPaymentView.as_view(), name='api_verify_payment'),
    path('wallet/recharge/create-order/', api_views.WalletRechargeOrderView.as_view(), name='api_wallet_order'),
    path('wallet/recharge/verify/', api_views.WalletRechargeVerifyView.as_view(), name='api_wallet_verify'),
]

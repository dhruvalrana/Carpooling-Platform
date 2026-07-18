"""Payments API views."""
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from trips.models import Trip
from .services import create_razorpay_order, verify_and_complete_payment, recharge_wallet
from core.exceptions import PaymentVerificationFailed


class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, trip_pk):
        trip = get_object_or_404(Trip, pk=trip_pk, passenger=request.user)
        order = create_razorpay_order(
            trip.fare_amount,
            notes={'trip_id': trip_pk, 'user': request.user.email},
        )
        return Response({'order_id': order['id'], 'amount': order['amount']})


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, trip_pk):
        trip = get_object_or_404(Trip, pk=trip_pk, passenger=request.user)
        try:
            payment = verify_and_complete_payment(
                trip,
                method=request.data.get('method', 'CARD'),
                order_id=request.data.get('razorpay_order_id', ''),
                payment_id=request.data.get('razorpay_payment_id', ''),
                signature=request.data.get('razorpay_signature', ''),
            )
            return Response({'status': 'success', 'payment_id': payment.id})
        except PaymentVerificationFailed as e:
            return Response({'error': str(e)}, status=400)


class WalletRechargeOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = Decimal(request.data.get('amount', '0'))
        if amount <= 0:
            return Response({'error': 'Invalid amount'}, status=400)
        order = create_razorpay_order(amount, notes={'user': request.user.email, 'type': 'wallet_recharge'})
        return Response({'order_id': order['id'], 'amount': order['amount']})


class WalletRechargeVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = Decimal(request.data.get('amount', '0'))
        try:
            wallet = recharge_wallet(
                user=request.user,
                amount=amount,
                order_id=request.data.get('razorpay_order_id', ''),
                payment_id=request.data.get('razorpay_payment_id', ''),
                signature=request.data.get('razorpay_signature', ''),
            )
            return Response({'balance': str(wallet.balance)})
        except PaymentVerificationFailed as e:
            return Response({'error': str(e)}, status=400)

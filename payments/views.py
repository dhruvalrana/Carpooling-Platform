"""Payment views — method selection and processing."""
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.conf import settings
from trips.models import Trip
from .models import Payment
from .services import (
    create_razorpay_order, process_cash_payment,
    process_wallet_payment, verify_and_complete_payment,
)
from core.exceptions import InsufficientWalletBalance, PaymentVerificationFailed


@login_required
def payment_screen(request, trip_pk):
    trip = get_object_or_404(Trip, pk=trip_pk, passenger=request.user)
    if trip.status != Trip.STATUS_PAYMENT_PENDING:
        messages.info(request, 'This trip is not pending payment.')
        return redirect('trip_detail', pk=trip_pk)

    # Get or create wallet
    from wallet.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=request.user)

    context = {
        'trip': trip,
        'wallet': wallet,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'payments/payment.html', context)


@login_required
@require_POST
def process_payment(request, trip_pk):
    trip = get_object_or_404(Trip, pk=trip_pk, passenger=request.user)
    if trip.status != Trip.STATUS_PAYMENT_PENDING:
        messages.error(request, 'Payment not applicable for this trip.')
        return redirect('trip_detail', pk=trip_pk)

    method = request.POST.get('method')

    try:
        if method == Payment.METHOD_CASH:
            process_cash_payment(trip)
            messages.success(request, 'Cash payment confirmed.')
            return redirect('trip_detail', pk=trip_pk)

        elif method == Payment.METHOD_WALLET:
            process_wallet_payment(trip, request.user)
            messages.success(request, f'₹{trip.fare_amount} debited from wallet.')
            return redirect('trip_detail', pk=trip_pk)

        elif method in (Payment.METHOD_CARD, Payment.METHOD_UPI):
            # Create Razorpay order
            order = create_razorpay_order(
                trip.fare_amount,
                notes={'trip_id': trip_pk, 'passenger': request.user.email},
            )
            return render(request, 'payments/razorpay_checkout.html', {
                'trip': trip,
                'order': order,
                'method': method,
                'razorpay_key': settings.RAZORPAY_KEY_ID,
            })

        else:
            messages.error(request, 'Invalid payment method.')

    except InsufficientWalletBalance as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f'Payment error: {e}')

    return redirect('payment_screen', trip_pk=trip_pk)


@login_required
@require_POST
def verify_payment(request, trip_pk):
    """Called after Razorpay Checkout.js completes — verify server-side."""
    trip = get_object_or_404(Trip, pk=trip_pk, passenger=request.user)
    order_id = request.POST.get('razorpay_order_id', '')
    payment_id = request.POST.get('razorpay_payment_id', '')
    signature = request.POST.get('razorpay_signature', '')
    method = request.POST.get('method', Payment.METHOD_CARD)

    try:
        verify_and_complete_payment(trip, method, order_id, payment_id, signature)
        messages.success(request, 'Payment successful! Trip completed.')
        return redirect('trip_detail', pk=trip_pk)
    except PaymentVerificationFailed:
        messages.error(request, 'Payment verification failed. Please contact support.')
        return redirect('payment_screen', trip_pk=trip_pk)

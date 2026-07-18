"""Wallet views."""
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Wallet, WalletTransaction
from payments.services import create_razorpay_order


@login_required
def wallet_view(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.order_by('-created_at')[:20]
    return render(request, 'wallet/wallet.html', {
        'wallet': wallet,
        'transactions': transactions,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
    })


@login_required
@require_POST
def initiate_recharge(request):
    """Create a Razorpay order for wallet recharge and render checkout."""
    amount_str = request.POST.get('amount', '0')
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            raise ValueError
    except Exception:
        messages.error(request, 'Enter a valid recharge amount.')
        return redirect('wallet')

    order = create_razorpay_order(amount, notes={'type': 'wallet_recharge', 'user': request.user.email})
    return render(request, 'payments/razorpay_checkout.html', {
        'order': order,
        'amount': amount,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'is_wallet_recharge': True,
    })

"""Payments service — Razorpay integration and wallet debit."""
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from core.exceptions import InsufficientWalletBalance, PaymentVerificationFailed
from .models import Payment
from wallet.models import Wallet, WalletTransaction


def get_razorpay_client():
    import razorpay
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def create_razorpay_order(amount_inr: Decimal, notes: dict = None) -> dict:
    """Create a Razorpay order. Amount is in INR (paise internally)."""
    client = get_razorpay_client()
    amount_paise = int(amount_inr * 100)
    order = client.order.create({
        'amount': amount_paise,
        'currency': 'INR',
        'notes': notes or {},
    })
    return order


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify Razorpay HMAC-SHA256 signature server-side. Never trust client claims."""
    key = settings.RAZORPAY_KEY_SECRET.encode()
    msg = f'{order_id}|{payment_id}'.encode()
    expected = hmac.new(key, msg, hashlib.sha256).hexdigest()  # noqa — hmac.new is the correct API
    return hmac.compare_digest(expected, signature)


@transaction.atomic
def process_cash_payment(trip) -> Payment:
    """Driver marks cash received — no gateway needed."""
    from trips.services import transition
    from trips.models import Trip
    payment = Payment.objects.create(
        trip=trip,
        method=Payment.METHOD_CASH,
        amount=trip.fare_amount,
        status=Payment.STATUS_SUCCESS,
    )
    transition(trip, Trip.STATUS_PAYMENT_COMPLETED, actor=None)
    return payment


@transaction.atomic
def process_wallet_payment(trip, passenger) -> Payment:
    """Debit wallet atomically with select_for_update."""
    from trips.services import transition
    from trips.models import Trip

    wallet = Wallet.objects.select_for_update().get_or_create(user=passenger)[0]
    if wallet.balance < trip.fare_amount:
        raise InsufficientWalletBalance(
            f'Insufficient wallet balance. Balance: ₹{wallet.balance}, Required: ₹{trip.fare_amount}'
        )

    wallet.balance -= trip.fare_amount
    wallet.save(update_fields=['balance'])

    WalletTransaction.objects.create(
        wallet=wallet,
        amount=trip.fare_amount,
        type=WalletTransaction.TYPE_DEBIT,
        reason=f'Payment for Trip #{trip.pk}',
        related_trip=trip,
    )

    payment = Payment.objects.create(
        trip=trip,
        method=Payment.METHOD_WALLET,
        amount=trip.fare_amount,
        status=Payment.STATUS_SUCCESS,
    )
    transition(trip, Trip.STATUS_PAYMENT_COMPLETED, actor=passenger)
    return payment


@transaction.atomic
def verify_and_complete_payment(trip, method, order_id, payment_id, signature) -> Payment:
    """Verify Razorpay payment server-side and complete trip."""
    from trips.services import transition
    from trips.models import Trip

    if not verify_razorpay_signature(order_id, payment_id, signature):
        raise PaymentVerificationFailed('Payment signature verification failed.')

    payment = Payment.objects.create(
        trip=trip,
        method=method,
        amount=trip.fare_amount,
        status=Payment.STATUS_SUCCESS,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
    )
    transition(trip, Trip.STATUS_PAYMENT_COMPLETED, actor=None)
    return payment


@transaction.atomic
def recharge_wallet(user, amount: Decimal, order_id: str, payment_id: str, signature: str):
    """Verify Razorpay signature then credit wallet."""
    if not verify_razorpay_signature(order_id, payment_id, signature):
        raise PaymentVerificationFailed('Wallet recharge signature verification failed.')

    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
    wallet.balance += amount
    wallet.save(update_fields=['balance'])

    WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        type=WalletTransaction.TYPE_CREDIT,
        reason='Wallet recharge via Razorpay',
    )
    return wallet

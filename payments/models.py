"""Payment model — lives in payments app for clarity."""
from django.db import models
from core.models import TimeStampedModel


class Payment(TimeStampedModel):
    METHOD_CASH = 'CASH'
    METHOD_CARD = 'CARD'
    METHOD_UPI = 'UPI'
    METHOD_WALLET = 'WALLET'
    METHOD_CHOICES = [
        (METHOD_CASH, 'Cash'),
        (METHOD_CARD, 'Card'),
        (METHOD_UPI, 'UPI'),
        (METHOD_WALLET, 'Wallet'),
    ]
    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
    ]

    trip = models.ForeignKey('trips.Trip', on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    razorpay_order_id = models.CharField(max_length=100, blank=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f'Payment #{self.pk} ₹{self.amount} via {self.method} [{self.status}]'

    class Meta:
        ordering = ['-created_at']

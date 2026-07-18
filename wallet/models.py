"""Wallet and WalletTransaction models."""
from django.db import models
from core.models import TimeStampedModel


class Wallet(TimeStampedModel):
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='wallet',
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'Wallet({self.user.get_full_name()}) ₹{self.balance}'


class WalletTransaction(TimeStampedModel):
    TYPE_CREDIT = 'CREDIT'
    TYPE_DEBIT = 'DEBIT'
    TYPE_CHOICES = [
        (TYPE_CREDIT, 'Credit'),
        (TYPE_DEBIT, 'Debit'),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    reason = models.CharField(max_length=200)
    related_trip = models.ForeignKey(
        'trips.Trip',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions',
    )

    def __str__(self):
        return f'{self.type} ₹{self.amount} — {self.reason}'

    class Meta:
        ordering = ['-created_at']

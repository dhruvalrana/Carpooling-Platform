"""Trip model — a booking instance (one passenger on one ride)."""
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel


class Trip(TimeStampedModel):
    STATUS_BOOKED = 'BOOKED'
    STATUS_STARTED = 'STARTED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_PAYMENT_PENDING = 'PAYMENT_PENDING'
    STATUS_PAYMENT_COMPLETED = 'PAYMENT_COMPLETED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (STATUS_BOOKED, 'Booked'),
        (STATUS_STARTED, 'Started'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PAYMENT_PENDING, 'Payment Pending'),
        (STATUS_PAYMENT_COMPLETED, 'Payment Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='trips',
    )
    passenger = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='booked_trips',
    )
    seats_booked = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_BOOKED)
    fare_amount = models.DecimalField(max_digits=10, decimal_places=2)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Trip #{self.pk}: {self.passenger.get_full_name()} on Ride #{self.ride_id} [{self.status}]'

    class Meta:
        ordering = ['-created_at']


class Message(TimeStampedModel):
    """In-trip chat message."""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    body = models.TextField()
    sent_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'[{self.sent_at:%H:%M}] {self.sender.get_full_name()}: {self.body[:50]}'

    class Meta:
        ordering = ['sent_at']

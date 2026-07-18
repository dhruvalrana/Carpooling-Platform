"""Ride model — the published offer (supply side)."""
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel


class Ride(TimeStampedModel):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_FULL = 'FULL'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_EXPIRED = 'EXPIRED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_FULL, 'Full'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    driver = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='offered_rides',
    )
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.CASCADE,
        related_name='rides',
    )
    # Pickup
    pickup_label = models.CharField(max_length=255)
    pickup_lat = models.FloatField()
    pickup_lng = models.FloatField()
    # Destination
    destination_label = models.CharField(max_length=255)
    destination_lat = models.FloatField()
    destination_lng = models.FloatField()
    # Schedule
    departure_datetime = models.DateTimeField()
    # Seats
    seats_total = models.PositiveSmallIntegerField()
    seats_available = models.PositiveSmallIntegerField()
    fare_per_seat = models.DecimalField(max_digits=10, decimal_places=2)
    # Recurrence
    is_recurring = models.BooleanField(default=False)
    recurrence_days = models.PositiveSmallIntegerField(default=5, null=True, blank=True,
                                                        help_text='Repeat for next N weekdays')
    # Route geometry (cached from mapping API)
    route_geometry = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    def is_full(self):
        return self.seats_available <= 0

    def __str__(self):
        return f'{self.driver.get_full_name()} | {self.pickup_label} -> {self.destination_label} @ {self.departure_datetime:%Y-%m-%d %H:%M}'

    class Meta:
        ordering = ['departure_datetime']

"""Vehicle model."""
from django.db import models
from core.models import TimeStampedModel


class Vehicle(TimeStampedModel):
    owner = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='vehicles',
    )
    make = models.CharField(max_length=100, verbose_name='Make/Brand')
    model = models.CharField(max_length=100, verbose_name='Model')
    registration_number = models.CharField(max_length=20, unique=True)
    seating_capacity = models.PositiveSmallIntegerField(
        default=4,
        help_text='Number of passenger seats (excluding driver)',
    )
    color = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.make} {self.model} - {self.registration_number}'

    class Meta:
        ordering = ['-created_at']

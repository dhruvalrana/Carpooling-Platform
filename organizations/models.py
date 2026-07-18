"""Organization and OrgSettings models."""
from django.db import models
from core.models import TimeStampedModel


class Organization(TimeStampedModel):
    """A registered company/org on the platform."""
    name = models.CharField(max_length=200)
    domain = models.CharField(
        max_length=100,
        unique=True,
        help_text='Email domain for auto-org-detection (e.g. acme.com)',
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class OrgSettings(TimeStampedModel):
    """Per-org configurable settings."""
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='settings',
    )
    fuel_cost_per_km = models.DecimalField(
        max_digits=10, decimal_places=2, default=8.00,
        help_text='Cost per km in org currency',
    )
    currency = models.CharField(max_length=10, default='INR')
    max_search_radius_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=5.00,
        help_text='Max pickup radius in km for ride search',
    )
    booking_cutoff_minutes = models.PositiveIntegerField(
        default=30,
        help_text='Minutes before departure after which booking is closed',
    )

    def __str__(self):
        return f'Settings for {self.organization.name}'

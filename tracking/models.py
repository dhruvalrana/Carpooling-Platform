"""LocationPing model for live tracking."""
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel


class LocationPing(TimeStampedModel):
    ride = models.ForeignKey('rides.Ride', on_delete=models.CASCADE, related_name='pings')
    lat = models.FloatField()
    lng = models.FloatField()
    heading = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True, help_text='km/h')
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-recorded_at']
        get_latest_by = 'recorded_at'

    def __str__(self):
        return f'Ping ride#{self.ride_id} @ {self.lat},{self.lng}'

"""Notification model."""
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel


class Notification(TimeStampedModel):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=50)
    payload = models.JSONField(default=dict)
    read_at = models.DateTimeField(null=True, blank=True)

    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])

    def __str__(self):
        return f'Notif({self.user}, {self.type})'

    class Meta:
        ordering = ['-created_at']

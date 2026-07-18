"""Custom User model — must be set as AUTH_USER_MODEL before first migration."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from core.models import TimeStampedModel


class User(AbstractUser):
    """
    Extended user with org membership and role.
    AbstractUser already provides: username, email, first_name, last_name,
    is_staff, is_active, date_joined.
    """
    ROLE_ADMIN = 'ADMIN'
    ROLE_EMPLOYEE = 'EMPLOYEE'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Organization Admin'),
        (ROLE_EMPLOYEE, 'Employee'),
    ]

    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=ROLE_EMPLOYEE,
    )
    phone = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    is_active_on_platform = models.BooleanField(default=True)

    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def is_employee(self):
        return self.role == self.ROLE_EMPLOYEE

    def get_full_name(self):
        name = super().get_full_name()
        return name or self.username

    def __str__(self):
        return f'{self.get_full_name()} ({self.email})'

    class Meta:
        ordering = ['first_name', 'last_name']


class SavedPlace(TimeStampedModel):
    user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='saved_places',
    )
    label = models.CharField(max_length=100)  # Home, Office, etc.
    address = models.CharField(max_length=255)
    lat = models.FloatField()
    lng = models.FloatField()

    def __str__(self):
        return f'{self.label}: {self.address}'

    class Meta:
        ordering = ['label']


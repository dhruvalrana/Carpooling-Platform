from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from decimal import Decimal

class Employee(AbstractUser):
    ROLE_CHOICES = [
        ('EMPLOYEE', 'Employee'),
        ('ADMIN', 'Company Administrator'),
    ]
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    department = models.CharField(max_length=100, null=True, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='EMPLOYEE')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.employee_id or 'No ID'})"

class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('TWO', 'Two-Wheeler'),
        ('THREE', 'Three-Wheeler'),
        ('FOUR', 'Four-Wheeler'),
    ]
    
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vehicles')
    make = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    license_plate = models.CharField(max_length=20, unique=True)
    capacity = models.PositiveIntegerField(default=4)
    color = models.CharField(max_length=30)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES, default='FOUR')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.color} {self.make} {self.model} ({self.license_plate})"

class SavedPlace(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_places')
    name = models.CharField(max_length=100) # e.g. Home, Office, Gym
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    def __str__(self):
        return f"{self.name}: {self.address}"

class Ride(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PUBLISHED', 'Published'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    driver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rides_driven')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    start_point_name = models.CharField(max_length=255)
    end_point_name = models.CharField(max_length=255)
    start_lat = models.DecimalField(max_digits=9, decimal_places=6)
    start_lng = models.DecimalField(max_digits=9, decimal_places=6)
    end_lat = models.DecimalField(max_digits=9, decimal_places=6)
    end_lng = models.DecimalField(max_digits=9, decimal_places=6)
    departure_time = models.DateTimeField()
    total_seats = models.PositiveIntegerField(default=4)
    seats_available = models.PositiveIntegerField(default=4)
    fare_per_seat = models.DecimalField(max_digits=6, decimal_places=2)
    price_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.40"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PUBLISHED')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ride from {self.start_point_name} to {self.end_point_name} by {self.driver}"

class Trip(models.Model):
    STATUS_CHOICES = [
        ('BOOKED', 'Ride Booked'),
        ('STARTED', 'Trip Started'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('PAYMENT_PENDING', 'Payment Pending'),
        ('PAYMENT_COMPLETED', 'Payment Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    passenger = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='trips')
    seats_booked = models.PositiveIntegerField(default=1)
    fare_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='BOOKED')
    rating_by_passenger = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking #{self.id} on Ride {self.ride.id} by {self.passenger.username}"

class TripChat(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message by {self.sender.username} at {self.timestamp}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('RECHARGE', 'Wallet Recharge'),
        ('PAYMENT', 'Trip Payment'),
        ('EARNED', 'Trip Earning'),
    ]
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    trip = models.ForeignKey(Trip, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} of {self.amount} for {self.employee.username}"

class SystemConfig(models.Model):
    org_name = models.CharField(max_length=100, default='Enterprise Corp')
    fuel_cost_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=12.00)
    travel_cost_per_km = models.DecimalField(max_digits=5, decimal_places=2, default=15.00)
    razorpay_key_id = models.CharField(max_length=100, default='rzp_test_mockkeyid123')
    razorpay_key_secret = models.CharField(max_length=100, default='mocksecret1234567890abcdef')

    def __str__(self):
        return f"Config for {self.org_name}"

    @classmethod
    def get_config(cls):
        config, created = cls.objects.get_or_create(id=1)
        return config

class Notification(models.Model):
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.employee.username}: {self.title}"

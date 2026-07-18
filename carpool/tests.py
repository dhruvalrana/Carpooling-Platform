from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Employee, Vehicle, Ride, Trip, Transaction, SystemConfig

class CarpoolTestCase(TestCase):
    def setUp(self):
        self.User = get_user_model()
        
        # Create Driver
        self.driver = self.User.objects.create_user(
            username="driver_test",
            email="driver@test.com",
            password="pass",
            first_name="Driver",
            last_name="Test",
            role="EMPLOYEE",
            wallet_balance=Decimal("100.00")
        )
        
        # Create Vehicle
        self.vehicle = Vehicle.objects.create(
            owner=self.driver,
            make="Honda",
            model="Civic",
            license_plate="PLATE123",
            capacity=3,
            color="Blue"
        )
        
        # Create Passenger
        self.passenger = self.User.objects.create_user(
            username="passenger_test",
            email="passenger@test.com",
            password="pass",
            first_name="Passenger",
            last_name="Test",
            role="EMPLOYEE",
            wallet_balance=Decimal("50.00")
        )
        
        # System Config
        self.config = SystemConfig.objects.create(
            org_name="Test Corp",
            fuel_cost_per_km=Decimal("10.00"),
            travel_cost_per_km=Decimal("12.00")
        )

    def test_employee_and_vehicle_creation(self):
        self.assertEqual(self.driver.wallet_balance, Decimal("100.00"))
        self.assertEqual(self.vehicle.capacity, 3)
        self.assertEqual(self.vehicle.owner, self.driver)

    def test_ride_and_booking_transaction(self):
        # Driver publishes ride
        departure = timezone.now() + timedelta(hours=5)
        ride = Ride.objects.create(
            driver=self.driver,
            vehicle=self.vehicle,
            start_point_name="A",
            end_point_name="B",
            start_lat=Decimal("37.0"),
            start_lng=Decimal("-122.0"),
            end_lat=Decimal("37.1"),
            end_lng=Decimal("-122.1"),
            departure_time=departure,
            total_seats=3,
            seats_available=3,
            fare_per_seat=Decimal("15.00"),
            status="PUBLISHED"
        )
        
        # Passenger books 1 seat
        fare = ride.fare_per_seat * 1
        self.passenger.wallet_balance -= fare
        self.passenger.save()
        ride.seats_available -= 1
        ride.save()
        
        trip = Trip.objects.create(
            passenger=self.passenger,
            ride=ride,
            seats_booked=1,
            fare_paid=fare,
            status="BOOKED"
        )
        
        Transaction.objects.create(
            employee=self.passenger,
            amount=-fare,
            transaction_type="PAYMENT",
            trip=trip
        )

        self.assertEqual(self.passenger.wallet_balance, Decimal("35.00"))
        self.assertEqual(ride.seats_available, 2)
        self.assertEqual(trip.fare_paid, Decimal("15.00"))
        self.assertEqual(Transaction.objects.filter(employee=self.passenger).count(), 1)

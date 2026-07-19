from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from .models import Employee, Vehicle, Ride, Trip, Transaction, SystemConfig, RideRequest

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

    def test_ride_request_and_matching(self):
        from .models import RideRequest
        
        # 1. Create a ride request
        req = RideRequest.objects.create(
            passenger=self.passenger,
            start_point_name="A",
            start_lat=Decimal("37.0"),
            start_lng=Decimal("-122.0"),
            end_point_name="B",
            end_lat=Decimal("37.1"),
            end_lng=Decimal("-122.1"),
            seats=1,
            vehicle_type="FOUR",
            estimated_price=Decimal("20.00"),
            status="PENDING"
        )
        
        self.assertEqual(req.status, "PENDING")
        
        # 2. Driver accepts request
        self.client.force_login(self.driver)
        response = self.client.post(f'/rides/request/{req.id}/accept/')
        
        # Verify redirect
        self.assertEqual(response.status_code, 302)
        
        # Verify request status changed
        req.refresh_from_db()
        self.assertEqual(req.status, "ACCEPTED")
        
        # Verify matching Ride and Trip created
        self.assertTrue(Ride.objects.filter(driver=self.driver, end_point_name="B").exists())
        trip = Trip.objects.filter(passenger=self.passenger, fare_paid=Decimal("20.00")).first()
        self.assertIsNotNone(trip)
        self.assertIsNotNone(trip.otp_code)
        self.assertEqual(len(trip.otp_code), 6)
        
        # 3. Try to start the trip with an invalid OTP code
        response = self.client.post(f'/trips/{trip.id}/update-status/', {
            'status': 'STARTED',
            'otp_code': '999999'
        })
        self.assertEqual(response.status_code, 302)
        trip.refresh_from_db()
        self.assertEqual(trip.status, "BOOKED")
        
        # 4. Start the trip with the correct OTP code
        response = self.client.post(f'/trips/{trip.id}/update-status/', {
            'status': 'STARTED',
            'otp_code': trip.otp_code
        })
        self.assertEqual(response.status_code, 302)
        trip.refresh_from_db()
        self.assertEqual(trip.status, "STARTED")

    def test_ride_offer_management(self):
        # Create published ride
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
        
        self.client.force_login(self.driver)
        
        # 1. Update ride offer
        response = self.client.post(f'/rides/offer/{ride.id}/update/', {
            'seats_available': 4,
            'departure_time': (departure + timedelta(hours=1)).isoformat()
        })
        self.assertEqual(response.status_code, 302)
        ride.refresh_from_db()
        self.assertEqual(ride.seats_available, 4)
        
        # 2. Cancel/Disable ride offer
        response = self.client.post(f'/rides/offer/{ride.id}/cancel/')
        self.assertEqual(response.status_code, 302)
        ride.refresh_from_db()
        self.assertEqual(ride.status, "CANCELLED")

    def test_upi_payment_flow(self):
        # 1. Create a ride request with payment_method='UPI'
        req = RideRequest.objects.create(
            passenger=self.passenger,
            start_point_name="A",
            start_lat=Decimal("37.0"),
            start_lng=Decimal("-122.0"),
            end_point_name="B",
            end_lat=Decimal("37.1"),
            end_lng=Decimal("-122.1"),
            seats=1,
            estimated_price=Decimal("25.00"),
            payment_method="UPI",
            status="PENDING"
        )
        
        # 2. Driver accepts request
        self.client.force_login(self.driver)
        response = self.client.post(f'/rides/request/{req.id}/accept/')
        self.assertEqual(response.status_code, 302)
        
        # Verify trip has payment_method='UPI'
        trip = Trip.objects.filter(passenger=self.passenger, fare_paid=Decimal("25.00")).first()
        self.assertIsNotNone(trip)
        self.assertEqual(trip.payment_method, "UPI")
        self.assertEqual(trip.status, "BOOKED")
        
        # 3. Start trip
        response = self.client.post(f'/trips/{trip.id}/update-status/', {
            'status': 'STARTED',
            'otp_code': trip.otp_code
        })
        self.assertEqual(response.status_code, 302)
        trip.refresh_from_db()
        self.assertEqual(trip.status, "STARTED")
        
        # 4. Driver completes trip (should transition to PAYMENT_PENDING for UPI)
        response = self.client.post(f'/trips/{trip.id}/update-status/', {
            'status': 'COMPLETED'
        })
        self.assertEqual(response.status_code, 302)
        trip.refresh_from_db()
        self.assertEqual(trip.status, "PAYMENT_PENDING")
        
        # 5. Passenger settles payment via UPI checkout
        self.client.force_login(self.passenger)
        response = self.client.post(f'/payments/{trip.id}/', {
            'payment_method': 'upi',
            'upi_id': 'test@upi'
        })
        self.assertEqual(response.status_code, 302)
        
        trip.refresh_from_db()
        self.assertEqual(trip.status, "PAYMENT_COMPLETED")
        
        # Check driver was credited
        self.driver.refresh_from_db()
        self.assertEqual(self.driver.wallet_balance, Decimal("125.00"))

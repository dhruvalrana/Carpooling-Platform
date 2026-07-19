from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from carpool.models import Employee, Vehicle, SavedPlace, Ride, Trip, Transaction, SystemConfig, TripChat

class Command(BaseCommand):
    help = 'Seeds database with initial sample employees, vehicles, and system configs.'

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample data...")

        # 1. Clean existing records (Optional, let's keep database clean for seed)
        Employee.objects.all().exclude(is_superuser=True).delete()
        Vehicle.objects.all().delete()
        SavedPlace.objects.all().delete()
        Ride.objects.all().delete()
        Trip.objects.all().delete()
        Transaction.objects.all().delete()
        SystemConfig.objects.all().delete()

        # 2. System Config
        config = SystemConfig.objects.create(
            org_name="Enterprise Campus Corp",  
            fuel_cost_per_km=Decimal("12.50"),
            travel_cost_per_km=Decimal("15.00")
        )
        self.stdout.write("Created SystemConfig.")

        # 3. Create Admin
        admin = Employee.objects.create_user(
            username="admin",
            email="admin@campuscorp.com",
            password="admin123",
            first_name="Admin",
            last_name="Manager",
            employee_id="ADM001",
            department="Operations",
            role="ADMIN"
        )
        self.stdout.write("Created admin user (password: admin123).")

        # 4. Create Driver John Doe
        driver = Employee.objects.create_user(
            username="john_doe",
            email="john.doe@campuscorp.com",
            password="password123",
            first_name="John",
            last_name="Doe",
            employee_id="EMP501",
            department="Engineering",
            wallet_balance=Decimal("150.00"),
            role="EMPLOYEE",
            phone_number="+91 9876543210"
        )
        self.stdout.write("Created driver user: john_doe (password:password123     ).")

        # Create Vehicle for John Doe
        vehicle = Vehicle.objects.create(
            owner=driver,
            make="Toyota",
            model="Prius Hybrid",
            license_plate="CA 99XYZ",
            capacity=4,
            color="Silver Pearl",
            vehicle_type="FOUR"
        )
        self.stdout.write("Created Vehicle for John Doe.")

        # Saved Places for John Doe
        SavedPlace.objects.create(
            employee=driver,
            name="Home",
            address="Technology and Research, Gandhinagar",
            latitude=Decimal("23.238645"),
            longitude=Decimal("72.638945")
        )
        SavedPlace.objects.create(
            employee=driver,
            name="Campus HQ",
            address="Gota, Ahmedabad",
            latitude=Decimal("23.007906"),
            longitude=Decimal("72.517437")
        )

        # 5. Create Passenger Jane Smith
        passenger = Employee.objects.create_user(
            username="jane_smith",
            email="jane.smith@campuscorp.com",
            password="password123",
            first_name="Jane",
            last_name="Smith",
            employee_id="EMP822",
            department="Product Design",
            wallet_balance=Decimal("80.00"),
            role="EMPLOYEE",
            phone_number="+91 9999988888"
        )
        self.stdout.write("Created passenger user: jane_smith (password: password123).")

        # Saved Places for Jane Smith
        SavedPlace.objects.create(
            employee=passenger,
            name="Home Suburb",
            address="Technology and Research, Gandhinagar",
            latitude=Decimal("23.238645"),
            longitude=Decimal("72.638945")
        )
        SavedPlace.objects.create(
            employee=passenger,
            name="Office Campus",
            address="Gota, Ahmedabad",
            latitude=Decimal("23.007906"),
            longitude=Decimal("72.517437")
        )

        # 6. Create Historical Completed Ride & Booking to feed analytics reports
        departure_past = timezone.now() - timedelta(days=2)
        past_ride = Ride.objects.create(
            driver=driver,
            vehicle=vehicle,
            start_point_name="Technology and Research, Gandhinagar",
            end_point_name="Gota, Ahmedabad",
            start_lat=Decimal("23.238645"),
            start_lng=Decimal("72.638945"),
            end_lat=Decimal("23.007906"),
            end_lng=Decimal("72.517437"),
            departure_time=departure_past,
            total_seats=4,
            seats_available=3,
            price_per_km=Decimal("0.40"),
            fare_per_seat=Decimal("18.50"),
            status="COMPLETED"
        )

        past_trip = Trip.objects.create(
            passenger=passenger,
            ride=past_ride,
            seats_booked=1,
            fare_paid=Decimal("18.50"),
            status="PAYMENT_COMPLETED"
        )

        # Transaction entries for history logs
        Transaction.objects.create(
            employee=passenger,
            amount=Decimal("-18.50"),
            transaction_type="PAYMENT",
            trip=past_trip,
            timestamp=departure_past
        )
        Transaction.objects.create(
            employee=driver,
            amount=Decimal("18.50"),
            transaction_type="EARNED",
            trip=past_trip,
            timestamp=departure_past
        )

        # Add chats to past trip
        TripChat.objects.create(
            trip=past_trip,
            sender=passenger,
            message="Hey John, I will wait at the entrance gate!"
        )
        TripChat.objects.create(
            trip=past_trip,
            sender=driver,
            message="Sounds good Jane. Arriving in 5 mins."
        )

        # 7. Create Active Pending Ride for today
        departure_today = timezone.now() + timedelta(hours=2)
        active_ride = Ride.objects.create(
            driver=driver,
            vehicle=vehicle,
            start_point_name="Technology and Research, Gandhinagar",
            end_point_name="Gota, Ahmedabad",
            start_lat=Decimal("23.238645"),
            start_lng=Decimal("72.638945"),
            end_lat=Decimal("23.007906"),
            end_lng=Decimal("72.517437"),
            departure_time=departure_today,
            total_seats=4,
            seats_available=4,
            price_per_km=Decimal("0.40"),
            fare_per_seat=Decimal("18.50"),
            status="PUBLISHED"
        )
        self.stdout.write("Created Active Published Ride for John Doe.")

        self.stdout.write(self.style.SUCCESS("Database seeded successfully with test records!"))

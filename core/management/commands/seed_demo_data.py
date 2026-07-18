"""
Seed demo data — creates orgs, users, vehicles, rides, and a trip booking
so a judge can run the full demo flow without manual setup.

Usage: python manage.py seed_demo_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Command(BaseCommand):
    help = 'Seed demo data for hackathon demo'

    def handle(self, *args, **options):
        from organizations.models import Organization, OrgSettings
        from accounts.models import User
        from vehicles.models import Vehicle
        from rides.models import Ride

        self.stdout.write('Seeding demo data...')

        # -- Organization --
        org, _ = Organization.objects.get_or_create(
            domain='demo.com',
            defaults={'name': 'Demo Corp', 'is_active': True},
        )
        OrgSettings.objects.get_or_create(
            organization=org,
            defaults={
                'fuel_cost_per_km': Decimal('8.00'),
                'currency': 'INR',
                'max_search_radius_km': Decimal('10.00'),
                'booking_cutoff_minutes': 30,
            },
        )
        self.stdout.write(f'  [OK] Organization: {org.name} (@demo.com)')

        # -- Admin user --
        admin, created = User.objects.get_or_create(
            email='admin@demo.com',
            defaults={
                'username': 'admin@demo.com',
                'first_name': 'Org',
                'last_name': 'Admin',
                'organization': org,
                'role': User.ROLE_ADMIN,
                'phone': '+91 9000000001',
                'is_staff': True,
            },
        )
        if created:
            admin.set_password('demo1234')
            admin.save()
        self.stdout.write('  [OK] Admin: admin@demo.com / demo1234')

        # -- Driver employee --
        driver, created = User.objects.get_or_create(
            email='driver@demo.com',
            defaults={
                'username': 'driver@demo.com',
                'first_name': 'Arjun',
                'last_name': 'Sharma',
                'organization': org,
                'role': User.ROLE_EMPLOYEE,
                'phone': '+91 9000000002',
            },
        )
        if created:
            driver.set_password('demo1234')
            driver.save()
        self.stdout.write('  [OK] Driver: driver@demo.com / demo1234')

        # -- Passenger employee --
        passenger, created = User.objects.get_or_create(
            email='passenger@demo.com',
            defaults={
                'username': 'passenger@demo.com',
                'first_name': 'Priya',
                'last_name': 'Patel',
                'organization': org,
                'role': User.ROLE_EMPLOYEE,
                'phone': '+91 9000000003',
            },
        )
        if created:
            passenger.set_password('demo1234')
            passenger.save()
        self.stdout.write('  [OK] Passenger: passenger@demo.com / demo1234')

        # -- Wallet for passenger --
        from wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=passenger, defaults={'balance': Decimal('500.00')})
        if wallet.balance < 100:
            wallet.balance = Decimal('500.00')
            wallet.save()
        self.stdout.write(f'  [OK] Wallet: passenger has Rs.{wallet.balance}')

        # -- Vehicle --
        vehicle, _ = Vehicle.objects.get_or_create(
            registration_number='MH12AB1234',
            defaults={
                'owner': driver,
                'make': 'Maruti',
                'model': 'Swift',
                'seating_capacity': 4,
                'color': 'White',
            },
        )
        self.stdout.write(f'  [OK] Vehicle: {vehicle}')

        # -- Ride --
        departure = timezone.now() + timedelta(hours=2)
        ride, _ = Ride.objects.get_or_create(
            driver=driver,
            vehicle=vehicle,
            pickup_label='Andheri Station, Mumbai',
            defaults={
                'destination_label': 'Bandra Kurla Complex, Mumbai',
                'pickup_lat': 19.1136,
                'pickup_lng': 72.8697,
                'destination_lat': 19.0654,
                'destination_lng': 72.8676,
                'departure_datetime': departure,
                'seats_total': 3,
                'seats_available': 3,
                'fare_per_seat': Decimal('80.00'),
                'status': Ride.STATUS_ACTIVE,
            },
        )
        self.stdout.write(f'  [OK] Ride: {ride}')

        self.stdout.write(self.style.SUCCESS('\n[DONE] Demo data seeded successfully!'))
        self.stdout.write('\nDemo accounts:')
        self.stdout.write('  Admin:     admin@demo.com     / demo1234')
        self.stdout.write('  Driver:    driver@demo.com    / demo1234')
        self.stdout.write('  Passenger: passenger@demo.com / demo1234')
        self.stdout.write('\nRun: python manage.py runserver')

"""Reports service — aggregation queries for personal and org-level stats."""
from decimal import Decimal
from django.db.models import Count, Sum, Avg
from trips.models import Trip


def personal_summary(user) -> dict:
    """Compute personal trip stats for an employee."""
    trips = Trip.objects.filter(
        passenger=user,
        status=Trip.STATUS_PAYMENT_COMPLETED,
    )
    total_trips = trips.count()
    total_fare = trips.aggregate(total=Sum('fare_amount'))['total'] or Decimal('0')

    # Rough distance estimate: fare / fuel_cost_per_km
    try:
        fuel_cost = user.organization.settings.fuel_cost_per_km or Decimal('8')
    except Exception:
        fuel_cost = Decimal('8')

    total_distance_km = float(total_fare / fuel_cost) if fuel_cost else 0
    fuel_consumed_l = round(total_distance_km / 15, 2)  # assume 15 km/l

    # Last 6 trips for trend
    recent = list(trips.select_related('ride').order_by('-completed_at')[:6].values(
        'completed_at', 'fare_amount', 'ride__pickup_label', 'ride__destination_label',
    ))

    return {
        'total_trips': total_trips,
        'total_fare': total_fare,
        'total_distance_km': round(total_distance_km, 2),
        'fuel_consumed_l': fuel_consumed_l,
        'cost_per_km': round(float(total_fare) / max(total_distance_km, 1), 2),
        'recent': recent,
    }


def org_summary(org) -> dict:
    """Compute org-level aggregate stats for admin."""
    from accounts.models import User
    from vehicles.models import Vehicle

    member_count = User.objects.filter(organization=org, is_active_on_platform=True).count()
    vehicle_count = Vehicle.objects.filter(owner__organization=org, is_active=True).count()

    trips = Trip.objects.filter(
        ride__driver__organization=org,
        status=Trip.STATUS_PAYMENT_COMPLETED,
    )
    completed_trips = trips.count()
    total_revenue = trips.aggregate(total=Sum('fare_amount'))['total'] or Decimal('0')

    # Participation rate: unique employees who have taken or offered at least one trip
    from rides.models import Ride
    drivers_with_rides = Ride.objects.filter(driver__organization=org).values_list('driver_id', flat=True).distinct()
    passengers_with_trips = trips.values_list('passenger_id', flat=True).distinct()
    participants = len(set(list(drivers_with_rides) + list(passengers_with_trips)))
    participation_rate = round(participants / max(member_count, 1) * 100, 1)

    return {
        'member_count': member_count,
        'vehicle_count': vehicle_count,
        'completed_trips': completed_trips,
        'total_revenue': total_revenue,
        'participants': participants,
        'participation_rate': participation_rate,
    }

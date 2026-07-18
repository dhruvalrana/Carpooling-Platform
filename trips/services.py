"""Trip business logic — booking with seat-lock and status state machine."""
from django.db import transaction
from django.utils import timezone
from core.exceptions import RideFullException, IllegalTripTransition
from .models import Trip
from rides.models import Ride

# Valid transitions per the architecture state machine
TRANSITIONS = {
    Trip.STATUS_BOOKED: [Trip.STATUS_STARTED, Trip.STATUS_CANCELLED],
    Trip.STATUS_STARTED: [Trip.STATUS_IN_PROGRESS],
    Trip.STATUS_IN_PROGRESS: [Trip.STATUS_COMPLETED],
    Trip.STATUS_COMPLETED: [Trip.STATUS_PAYMENT_PENDING],
    Trip.STATUS_PAYMENT_PENDING: [Trip.STATUS_PAYMENT_COMPLETED],
    Trip.STATUS_PAYMENT_COMPLETED: [],
    Trip.STATUS_CANCELLED: [],
}


@transaction.atomic
def book_ride(passenger, ride_id: int, seats_needed: int = 1) -> Trip:
    """
    Book a ride for the given passenger.
    Uses select_for_update to prevent overbooking race conditions.
    """
    # Lock the ride row
    ride = Ride.objects.select_for_update().get(pk=ride_id)

    if ride.driver == passenger:
        raise ValueError("You cannot book your own ride.")

    if ride.status != Ride.STATUS_ACTIVE:
        raise RideFullException("This ride is no longer available.")

    if ride.seats_available < seats_needed:
        raise RideFullException(
            f"Only {ride.seats_available} seat(s) left on this ride."
        )

    # Check duplicate booking
    if Trip.objects.filter(ride=ride, passenger=passenger,
                           status__in=[Trip.STATUS_BOOKED, Trip.STATUS_STARTED,
                                       Trip.STATUS_IN_PROGRESS]).exists():
        raise ValueError("You have already booked this ride.")

    # Decrement seats
    ride.seats_available -= seats_needed
    if ride.seats_available == 0:
        ride.status = Ride.STATUS_FULL
    ride.save(update_fields=['seats_available', 'status'])

    # Create trip
    trip = Trip.objects.create(
        ride=ride,
        passenger=passenger,
        seats_booked=seats_needed,
        fare_amount=ride.fare_per_seat * seats_needed,
        status=Trip.STATUS_BOOKED,
    )
    return trip


@transaction.atomic
def transition(trip: Trip, new_status: str, actor) -> Trip:
    """
    Transition a trip to a new status.
    Validates the edge; raises IllegalTripTransition on invalid moves.
    """
    allowed = TRANSITIONS.get(trip.status, [])
    if new_status not in allowed:
        raise IllegalTripTransition(
            f"Cannot move trip from '{trip.status}' to '{new_status}'."
        )

    trip = Trip.objects.select_for_update().get(pk=trip.pk)
    trip.status = new_status
    if new_status == Trip.STATUS_STARTED:
        trip.started_at = timezone.now()
    elif new_status == Trip.STATUS_COMPLETED:
        trip.completed_at = timezone.now()
    trip.save()
    return trip

"""Notification dispatch service."""
from .models import Notification


def notify(user, type_: str, payload: dict = None):
    """Create an in-app notification for a user."""
    Notification.objects.create(
        user=user,
        type=type_,
        payload=payload or {},
    )


def notify_booking(trip):
    """Notify driver of a new booking."""
    notify(
        trip.ride.driver,
        type_='BOOKING',
        payload={
            'trip_id': trip.pk,
            'passenger': trip.passenger.get_full_name(),
            'seats': trip.seats_booked,
        },
    )


def notify_trip_started(trip):
    """Notify passenger that the driver has started."""
    notify(
        trip.passenger,
        type_='TRIP_STARTED',
        payload={'trip_id': trip.pk, 'driver': trip.ride.driver.get_full_name()},
    )

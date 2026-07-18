"""Tracking views — driver ping and passenger polling."""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from rides.models import Ride
from trips.models import Trip
from .models import LocationPing
import json


def _has_trip_access(user, ride):
    """Return True if user is the driver or a passenger of this ride."""
    if ride.driver == user:
        return True
    return Trip.objects.filter(ride=ride, passenger=user).exists()


@login_required
@require_POST
def ping(request):
    """Driver posts location ping."""
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    ride_id = data.get('ride_id')
    ride = get_object_or_404(Ride, pk=ride_id, driver=request.user)

    if ride.driver != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    # Only accept pings during active trip
    active_trip = Trip.objects.filter(
        ride=ride,
        status__in=[Trip.STATUS_STARTED, Trip.STATUS_IN_PROGRESS],
    ).first()
    if not active_trip:
        return JsonResponse({'error': 'No active trip for this ride'}, status=400)

    LocationPing.objects.create(
        ride=ride,
        lat=float(data['lat']),
        lng=float(data['lng']),
        heading=data.get('heading'),
        speed=data.get('speed'),
    )
    return JsonResponse({'status': 'ok'})


@login_required
def latest_ping(request, ride_id):
    """Passenger polls for latest driver location."""
    ride = get_object_or_404(Ride, pk=ride_id)

    if not _has_trip_access(request.user, ride):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        ping = LocationPing.objects.filter(ride=ride).latest()
        return JsonResponse({
            'lat': ping.lat,
            'lng': ping.lng,
            'heading': ping.heading,
            'speed': ping.speed,
            'recorded_at': ping.recorded_at.isoformat(),
        })
    except LocationPing.DoesNotExist:
        return JsonResponse({'error': 'No location data yet'}, status=404)

"""Rides business logic — geocoding, matching, route preview."""
import math
import requests
from django.conf import settings
from .models import Ride


def geocode(address: str) -> dict:
    """
    Convert address string to lat/lng using Nominatim (OpenStreetMap).
    Returns {'lat': float, 'lng': float, 'label': str} or raises ValueError.
    """
    url = 'https://nominatim.openstreetmap.org/search'
    params = {
        'q': address,
        'format': 'json',
        'limit': 1,
        'addressdetails': 1,
    }
    headers = {'User-Agent': 'CarpoolPlatform/1.0 (hackathon)'}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        results = resp.json()
        if results:
            r = results[0]
            return {
                'lat': float(r['lat']),
                'lng': float(r['lon']),
                'label': r.get('display_name', address)[:255],
            }
    except Exception:
        pass
    raise ValueError(f'Could not geocode: {address}')


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    """Calculate great-circle distance between two lat/lng points in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def search_rides(
    org,
    pickup_lat, pickup_lng,
    dest_lat, dest_lng,
    departure_date,
    departure_time,
    seats_needed,
    time_window_minutes=60,
):
    """
    Find matching active rides in the org.
    Filters: org, date/time window, seats, pickup radius.
    Returns queryset ordered by time proximity.
    """
    from datetime import datetime, timedelta
    from django.utils import timezone as tz

    # Build datetime window
    naive_dt = datetime.combine(departure_date, departure_time)
    target_dt = tz.make_aware(naive_dt)
    window_start = target_dt - timedelta(minutes=time_window_minutes)
    window_end = target_dt + timedelta(minutes=time_window_minutes)

    # Get org settings for radius
    try:
        max_radius = float(org.settings.max_search_radius_km)
    except Exception:
        max_radius = 5.0

    candidates = Ride.objects.filter(
        driver__organization=org,
        status=Ride.STATUS_ACTIVE,
        seats_available__gte=seats_needed,
        departure_datetime__range=(window_start, window_end),
    ).select_related('driver', 'vehicle')

    # Filter by pickup proximity
    results = []
    for ride in candidates:
        dist = haversine_km(pickup_lat, pickup_lng, ride.pickup_lat, ride.pickup_lng)
        if dist <= max_radius:
            results.append((dist, ride))

    # Sort by pickup distance, then departure time proximity
    results.sort(key=lambda x: x[0])
    return [r[1] for r in results]


def get_route_preview(pickup_lat, pickup_lng, dest_lat, dest_lng) -> dict:
    """
    Get route geometry from OSRM public demo server.
    Returns {'distance_km': float, 'duration_min': float, 'geometry': list}
    """
    url = (
        f'https://router.project-osrm.org/route/v1/driving/'
        f'{pickup_lng},{pickup_lat};{dest_lng},{dest_lat}'
        f'?overview=full&geometries=geojson'
    )
    try:
        resp = requests.get(url, timeout=8)
        data = resp.json()
        route = data['routes'][0]
        return {
            'distance_km': round(route['distance'] / 1000, 2),
            'duration_min': round(route['duration'] / 60, 1),
            'geometry': route['geometry']['coordinates'],
        }
    except Exception:
        return {'distance_km': None, 'duration_min': None, 'geometry': []}

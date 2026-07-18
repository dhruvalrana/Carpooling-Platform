"""Rides views — Offer, Find, Route Confirmation, Results."""
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Ride
from .forms import OfferRideForm, FindRideForm
from .services import geocode, search_rides, get_route_preview
from vehicles.models import Vehicle


@login_required
def offer_ride(request):
    """Step 1 — fill offer form."""
    vehicles = Vehicle.objects.filter(owner=request.user, is_active=True)
    if not vehicles.exists():
        messages.warning(request, 'You need to register a vehicle before offering a ride.')
        return redirect('add_vehicle')

    form = OfferRideForm(request.user, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        # Geocode if lat/lng not provided directly
        pickup = form.cleaned_data.get('pickup_label')
        dest = form.cleaned_data.get('destination_label')
        pickup_lat = form.cleaned_data.get('pickup_lat')
        pickup_lng = form.cleaned_data.get('pickup_lng')
        dest_lat = form.cleaned_data.get('destination_lat')
        dest_lng = form.cleaned_data.get('destination_lng')

        if not pickup_lat:
            try:
                geo = geocode(pickup)
                pickup_lat, pickup_lng = geo['lat'], geo['lng']
            except ValueError:
                form.add_error('pickup_label', 'Could not locate this address.')
                return render(request, 'rides/offer_ride.html', {'form': form})
        if not dest_lat:
            try:
                geo = geocode(dest)
                dest_lat, dest_lng = geo['lat'], geo['lng']
            except ValueError:
                form.add_error('destination_label', 'Could not locate this address.')
                return render(request, 'rides/offer_ride.html', {'form': form})

        # Store in session for route confirmation step
        request.session['offer_data'] = {
            **{k: str(v) for k, v in form.cleaned_data.items()
               if k not in ('vehicle',)},
            'vehicle_id': form.cleaned_data['vehicle'].id,
            'pickup_lat': pickup_lat,
            'pickup_lng': pickup_lng,
            'destination_lat': dest_lat,
            'destination_lng': dest_lng,
        }
        return redirect('route_confirm_offer')

    return render(request, 'rides/offer_ride.html', {'form': form})


@login_required
def route_confirm_offer(request):
    """Step 2 — confirm route, then publish."""
    data = request.session.get('offer_data')
    if not data:
        return redirect('offer_ride')

    route = get_route_preview(
        float(data['pickup_lat']), float(data['pickup_lng']),
        float(data['destination_lat']), float(data['destination_lng']),
    )

    if request.method == 'POST' and request.POST.get('confirm') == '1':
        vehicle = get_object_or_404(Vehicle, pk=data['vehicle_id'], owner=request.user)
        from datetime import datetime
        seats = int(data['seats_total'])
        ride = Ride.objects.create(
            driver=request.user,
            vehicle=vehicle,
            pickup_label=data['pickup_label'],
            pickup_lat=float(data['pickup_lat']),
            pickup_lng=float(data['pickup_lng']),
            destination_label=data['destination_label'],
            destination_lat=float(data['destination_lat']),
            destination_lng=float(data['destination_lng']),
            departure_datetime=data['departure_datetime'],
            seats_total=seats,
            seats_available=seats,
            fare_per_seat=data['fare_per_seat'],
            is_recurring=data.get('is_recurring') == 'True',
            route_geometry=route.get('geometry'),
        )
        del request.session['offer_data']
        messages.success(request, 'Your ride is now live!')
        return redirect('ride_detail', pk=ride.pk)

    context = {
        'data': data,
        'route': route,
        'geometry_json': json.dumps(route.get('geometry', [])),
    }
    return render(request, 'rides/route_confirm.html', context)


@login_required
def find_ride(request):
    """Step 1 — search form."""
    form = FindRideForm(data=request.GET or None)
    results = []
    route = None
    geometry_json = '[]'

    if request.GET and form.is_valid():
        cd = form.cleaned_data
        pickup_label = cd['pickup_label']
        dest_label = cd['destination_label']

        try:
            pickup_geo = geocode(pickup_label)
        except ValueError:
            form.add_error('pickup_label', 'Could not locate this address.')
            return render(request, 'rides/find_ride.html', {'form': form})
        try:
            dest_geo = geocode(dest_label)
        except ValueError:
            form.add_error('destination_label', 'Could not locate this address.')
            return render(request, 'rides/find_ride.html', {'form': form})

        route = get_route_preview(
            pickup_geo['lat'], pickup_geo['lng'],
            dest_geo['lat'], dest_geo['lng'],
        )
        geometry_json = json.dumps(route.get('geometry', []))

        results = search_rides(
            org=request.user.organization,
            pickup_lat=pickup_geo['lat'],
            pickup_lng=pickup_geo['lng'],
            dest_lat=dest_geo['lat'],
            dest_lng=dest_geo['lng'],
            departure_date=cd['departure_date'],
            departure_time=cd['departure_time'],
            seats_needed=cd['seats_needed'],
        )

    return render(request, 'rides/find_ride.html', {
        'form': form,
        'results': results,
        'route': route,
        'geometry_json': geometry_json,
    })


@login_required
def ride_detail(request, pk):
    ride = get_object_or_404(Ride, pk=pk)
    # Ensure org isolation
    if ride.driver.organization != request.user.organization:
        messages.error(request, 'Ride not found.')
        return redirect('find_ride')
    trips = ride.trips.select_related('passenger').all()
    return render(request, 'rides/ride_detail.html', {
        'ride': ride,
        'trips': trips,
        'is_driver': ride.driver == request.user,
        'geometry_json': json.dumps(ride.route_geometry or []),
    })


@login_required
def my_offered_rides(request):
    rides = Ride.objects.filter(driver=request.user).order_by('-created_at')
    return render(request, 'rides/my_offered_rides.html', {'rides': rides})

"""Trips views — My Trips, Trip Detail, booking, status transitions, chat."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from .models import Trip, Message
from .services import book_ride, transition
from rides.models import Ride
from core.exceptions import RideFullException, IllegalTripTransition
import json


@login_required
def my_trips(request):
    tab = request.GET.get('tab', 'upcoming')
    user = request.user

    if tab == 'upcoming':
        as_passenger = Trip.objects.filter(
            passenger=user,
            status__in=[Trip.STATUS_BOOKED],
        )
        as_driver = Trip.objects.filter(
            ride__driver=user,
            status__in=[Trip.STATUS_BOOKED],
        )
    elif tab == 'active':
        as_passenger = Trip.objects.filter(
            passenger=user,
            status__in=[Trip.STATUS_STARTED, Trip.STATUS_IN_PROGRESS],
        )
        as_driver = Trip.objects.filter(
            ride__driver=user,
            status__in=[Trip.STATUS_STARTED, Trip.STATUS_IN_PROGRESS],
        )
    else:  # completed
        as_passenger = Trip.objects.filter(
            passenger=user,
            status__in=[Trip.STATUS_COMPLETED, Trip.STATUS_PAYMENT_PENDING, Trip.STATUS_PAYMENT_COMPLETED],
        )
        as_driver = Trip.objects.filter(
            ride__driver=user,
            status__in=[Trip.STATUS_COMPLETED, Trip.STATUS_PAYMENT_PENDING, Trip.STATUS_PAYMENT_COMPLETED],
        )

    return render(request, 'trips/my_trips.html', {
        'tab': tab,
        'as_passenger': as_passenger.select_related('ride', 'ride__driver', 'ride__vehicle'),
        'as_driver': as_driver.select_related('ride', 'passenger'),
    })


@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    user = request.user

    # Access control — only driver or passenger of this trip
    if trip.passenger != user and trip.ride.driver != user:
        messages.error(request, 'Trip not found.')
        return redirect('my_trips')

    messages_qs = trip.messages.select_related('sender').order_by('sent_at')
    is_driver = trip.ride.driver == user

    context = {
        'trip': trip,
        'chat_messages': messages_qs,
        'is_driver': is_driver,
        'geometry_json': json.dumps(trip.ride.route_geometry or []),
        'statuses': [
            Trip.STATUS_BOOKED,
            Trip.STATUS_STARTED,
            Trip.STATUS_IN_PROGRESS,
            Trip.STATUS_COMPLETED,
            Trip.STATUS_PAYMENT_PENDING,
            Trip.STATUS_PAYMENT_COMPLETED,
        ],
    }
    return render(request, 'trips/trip_detail.html', context)


@login_required
@require_POST
def book_ride_view(request, ride_pk):
    ride = get_object_or_404(Ride, pk=ride_pk)
    seats = int(request.POST.get('seats', 1))
    try:
        trip = book_ride(request.user, ride.pk, seats)
        messages.success(request, f'Ride booked! Your trip #{trip.pk} is confirmed.')
        return redirect('trip_detail', pk=trip.pk)
    except (RideFullException, ValueError) as e:
        messages.error(request, str(e))
        return redirect('ride_detail', pk=ride_pk)


@login_required
@require_POST
def transition_trip(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    new_status = request.POST.get('status')
    user = request.user

    # Only driver can move most status; passenger can't start/complete
    if trip.ride.driver != user and new_status in [
        Trip.STATUS_STARTED, Trip.STATUS_IN_PROGRESS, Trip.STATUS_COMPLETED
    ]:
        messages.error(request, 'Only the driver can change trip status.')
        return redirect('trip_detail', pk=pk)

    try:
        transition(trip, new_status, actor=user)
        messages.success(request, f'Trip status updated to {new_status}.')
    except IllegalTripTransition as e:
        messages.error(request, str(e))

    return redirect('trip_detail', pk=pk)


@login_required
@require_POST
def send_chat(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    user = request.user
    if trip.passenger != user and trip.ride.driver != user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    body = request.POST.get('body', '').strip()
    if body:
        msg = Message.objects.create(trip=trip, sender=user, body=body)
        return JsonResponse({
            'id': msg.id,
            'sender': user.get_full_name(),
            'body': msg.body,
            'sent_at': msg.sent_at.isoformat(),
            'is_me': True,
        })
    return JsonResponse({'error': 'Empty message'}, status=400)


@login_required
def ride_history(request):
    user = request.user
    trips = Trip.objects.filter(
        passenger=user,
        status=Trip.STATUS_PAYMENT_COMPLETED,
    ).select_related('ride', 'ride__driver', 'ride__vehicle').order_by('-completed_at')
    return render(request, 'trips/ride_history.html', {'trips': trips})

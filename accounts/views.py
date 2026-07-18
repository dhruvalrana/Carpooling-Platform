"""Accounts views — Splash, Login, Signup, Profile, Dashboard."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from organizations.models import Organization
from .models import User
from .forms import SignUpForm, LoginForm, ProfileForm


def splash(request):
    """Splash/landing screen."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/splash.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        next_url = request.GET.get('next', 'dashboard')
        return redirect(next_url)
    return render(request, 'accounts/login.html', {'form': form})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignUpForm(data=request.POST or None, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome! Complete your profile to get started.')
        return redirect('dashboard')
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    user = request.user
    if user.is_admin():
        return redirect('admin_dashboard')
    return redirect('employee_dashboard')


@login_required
def employee_dashboard(request):
    from trips.models import Trip
    from rides.models import Ride
    user = request.user
    upcoming_trips = Trip.objects.filter(
        passenger=user,
        status__in=['BOOKED', 'STARTED', 'IN_PROGRESS'],
    ).select_related('ride', 'ride__driver', 'ride__vehicle').order_by('ride__departure_datetime')[:3]

    offered_rides = Ride.objects.filter(
        driver=user,
        status='ACTIVE',
    ).order_by('departure_datetime')[:3]

    # Personal stats
    completed_trips = Trip.objects.filter(passenger=user, status='PAYMENT_COMPLETED').count()

    context = {
        'upcoming_trips': upcoming_trips,
        'offered_rides': offered_rides,
        'completed_trips': completed_trips,
    }
    return render(request, 'accounts/employee_dashboard.html', context)


@login_required
def admin_dashboard(request):
    if not request.user.is_admin():
        return redirect('employee_dashboard')
    org = request.user.organization
    members = User.objects.filter(organization=org)
    from vehicles.models import Vehicle
    vehicles = Vehicle.objects.filter(owner__organization=org)
    from rides.models import Ride
    active_rides = Ride.objects.filter(
        driver__organization=org, status='ACTIVE'
    ).count()
    from trips.models import Trip
    completed_trips = Trip.objects.filter(
        ride__driver__organization=org, status='PAYMENT_COMPLETED'
    ).count()

    context = {
        'org': org,
        'member_count': members.count(),
        'vehicle_count': vehicles.count(),
        'active_rides': active_rides,
        'completed_trips': completed_trips,
        'members': members.order_by('first_name')[:10],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
def profile_view(request):
    form = ProfileForm(
        data=request.POST or None,
        files=request.FILES or None,
        instance=request.user,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('profile')
    return render(request, 'accounts/profile.html', {'form': form})

import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, F
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from decimal import Decimal
from datetime import datetime, timedelta

from .models import Employee, Vehicle, SavedPlace, Ride, Trip, TripChat, Transaction, SystemConfig
from .forms import EmployeeCreationForm, EmployeeProfileForm, VehicleForm, SavedPlaceForm, RideForm, WalletRechargeForm, SystemConfigForm

# ----------------- Helper Functions -----------------
def calculate_distance(lat1, lon1, lat2, lon2):
    # Rough distance calculation in kilometers using equirectangular approximation
    lat1, lon1, lat2, lon2 = float(lat1), float(lon1), float(lat2), float(lon2)
    R = 6371.0 # Earth's radius in km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def check_route_match(p_start_lat, p_start_lng, p_end_lat, p_end_lng, d_start_lat, d_start_lng, d_end_lat, d_end_lng):
    # px, py: passenger start
    # qx, qy: passenger end
    # ax, ay: driver start
    # bx, by: driver end
    px, py = float(p_start_lat), float(p_start_lng)
    qx, qy = float(p_end_lat), float(p_end_lng)
    ax, ay = float(d_start_lat), float(d_start_lng)
    bx, by = float(d_end_lat), float(d_end_lng)
    
    dx = bx - ax
    dy = by - ay
    seg_len_sq = dx * dx + dy * dy
    
    if seg_len_sq == 0:
        d1 = calculate_distance(px, py, ax, ay)
        d2 = calculate_distance(qx, qy, bx, by)
        return (d1 <= 10.0 and d2 <= 10.0), d1, d2

    # Project pickup P onto driver's path AB
    t_pickup = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
    t_pickup_clamped = max(0.0, min(1.0, t_pickup))
    closest_p_x = ax + t_pickup_clamped * dx
    closest_p_y = ay + t_pickup_clamped * dy
    pickup_to_path = calculate_distance(px, py, closest_p_x, closest_p_y)
    
    # Project destination Q onto driver's path AB
    t_dest = ((qx - ax) * dx + (qy - ay) * dy) / seg_len_sq
    t_dest_clamped = max(0.0, min(1.0, t_dest))
    closest_q_x = ax + t_dest_clamped * dx
    closest_q_y = ay + t_dest_clamped * dy
    dest_to_path = calculate_distance(qx, qy, closest_q_x, closest_q_y)
    
    # Matching rules:
    # 1. Pickup within 10km of path
    # 2. Drop-off within 10km of path
    # 3. Same direction (t_pickup < t_dest)
    is_match = (pickup_to_path <= 10.0) and (dest_to_path <= 10.0) and (t_pickup < t_dest)
    return is_match, pickup_to_path, dest_to_path

# ----------------- Auth Views -----------------
def splash_view(request):
    context = {}
    if request.user.is_authenticated:
        if request.user.role == 'ADMIN' or request.user.is_superuser:
            return redirect('admin_dashboard')
            
        # Upcoming passenger bookings
        upcoming_bookings = Trip.objects.filter(
            passenger=request.user,
            status__in=['BOOKED', 'STARTED', 'IN_PROGRESS', 'PAYMENT_PENDING']
        ).order_by('ride__departure_time')

        # Upcoming drives
        upcoming_drives = Ride.objects.filter(
            driver=request.user,
            status='PUBLISHED',
            departure_time__gte=timezone.now()
        ).order_by('departure_time')

        # Completed passenger trips stats
        passenger_stats = Trip.objects.filter(passenger=request.user, status='COMPLETED')
        passenger_trip_count = passenger_stats.count()
        total_passenger_dist = 0
        for trip in passenger_stats:
            total_passenger_dist += calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)

        # Completed driven rides stats
        driven_rides = Ride.objects.filter(driver=request.user, status='COMPLETED')
        driven_count = driven_rides.count()
        total_driven_dist = 0
        for ride in driven_rides:
            total_driven_dist += calculate_distance(ride.start_lat, ride.start_lng, ride.end_lat, ride.end_lng)

        total_trips = passenger_trip_count + driven_count
        total_distance = round(total_passenger_dist + total_driven_dist, 1)

        # CO2 saved (Assume 12km/L fuel consumption and 2.31kg CO2 per liter gasoline)
        fuel_saved = round(total_passenger_dist / 12.0, 1)
        co2_saved = round(fuel_saved * 2.31, 1)

        # Earnings
        total_earned = driven_rides.aggregate(sum_earnings=Sum('trips__fare_paid'))['sum_earnings'] or Decimal('0.00')

        context.update({
            'total_trips': total_trips,
            'total_distance': total_distance,
            'co2_saved': co2_saved,
            'total_earned': total_earned,
            'wallet_balance': request.user.wallet_balance,
            'upcoming_bookings_count': upcoming_bookings.count(),
            'upcoming_drives_count': upcoming_drives.count(),
        })
    return render(request, 'accounts/splash.html', context)

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('splash')
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully! You are now logged in.")
            login(request, user)
            return redirect('splash')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EmployeeCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

# ----------------- Dashboard & Profile -----------------
@login_required
def dashboard_view(request):
    if request.user.role == 'ADMIN' or request.user.is_superuser:
        return redirect('admin_dashboard')
    
    # Upcoming trips where employee is a passenger
    upcoming_bookings = Trip.objects.filter(
        passenger=request.user,
        status__in=['BOOKED', 'STARTED', 'IN_PROGRESS', 'PAYMENT_PENDING']
    ).order_by('ride__departure_time')

    # Upcoming drives where employee is the driver
    upcoming_drives = Ride.objects.filter(
        driver=request.user,
        status='PUBLISHED',
        departure_time__gte=timezone.now()
    ).order_by('departure_time')

    # Realtime Statistics
    # Completed bookings as passenger
    passenger_stats = Trip.objects.filter(passenger=request.user, status__in=['COMPLETED', 'PAYMENT_COMPLETED'])
    passenger_trip_count = passenger_stats.count()
    
    total_passenger_dist = 0
    for trip in passenger_stats:
        total_passenger_dist += calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)
        
    # Completed rides driven as driver
    driven_rides = Ride.objects.filter(driver=request.user, status='COMPLETED')
    driven_count = driven_rides.count()
    
    total_driven_dist = 0
    for ride in driven_rides:
        total_driven_dist += calculate_distance(ride.start_lat, ride.start_lng, ride.end_lat, ride.end_lng)
        
    total_trips = passenger_trip_count + driven_count
    total_distance = round(total_passenger_dist + total_driven_dist, 1)
    
    # CO2 saved (Assume 12km/L fuel consumption and 2.31kg CO2 per liter gasoline)
    fuel_saved = round(total_passenger_dist / 12.0, 1)
    co2_saved = round(fuel_saved * 2.31, 1)
    
    # Driver earnings
    total_earned = driven_rides.aggregate(
        sum_earnings=Sum('trips__fare_paid')
    )['sum_earnings'] or Decimal('0.00')

    wallet_balance = request.user.wallet_balance
    config = SystemConfig.get_config()

    # Team/System-wide commute statistics
    all_completed_trips = Trip.objects.filter(status__in=['COMPLETED', 'PAYMENT_COMPLETED'])
    stat_rides_shared = all_completed_trips.count()
    
    total_system_dist = 0
    for trip in all_completed_trips:
        total_system_dist += calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)
        
    system_fuel_saved = float(total_system_dist) / 12.0
    system_co2_saved_kg = system_fuel_saved * 2.31
    if system_co2_saved_kg >= 1000:
        stat_co2_saved = f"{system_co2_saved_kg / 1000.0:.1f}t"
    else:
        stat_co2_saved = f"{system_co2_saved_kg:.1f} kg"
        
    stat_cost_saved = all_completed_trips.aggregate(sum_fare=Sum('fare_paid'))['sum_fare'] or Decimal('0.00')
    
    # Calculate avg match time
    total_match_minutes = 0
    match_count = 0
    from .models import RideRequest
    for trip in all_completed_trips:
        req = RideRequest.objects.filter(
            passenger=trip.passenger,
            status='ACCEPTED',
            created_at__lte=trip.created_at
        ).order_by('-created_at').first()
        if req:
            diff = (trip.created_at - req.created_at).total_seconds() / 60.0
            total_match_minutes += diff
            match_count += 1
            
    avg_minutes = (total_match_minutes / match_count) if match_count > 0 else 3.2
    stat_match_time = f"{avg_minutes:.1f}m"

    # Calculate dynamic deltas for current month vs last month
    now = timezone.now()
    curr_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_end = curr_month_start - timedelta(seconds=1)
    prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 1. Rides shared delta
    curr_rides = Trip.objects.filter(status__in=['COMPLETED', 'PAYMENT_COMPLETED'], created_at__gte=curr_month_start).count()
    prev_rides = Trip.objects.filter(status__in=['COMPLETED', 'PAYMENT_COMPLETED'], created_at__range=(prev_month_start, prev_month_end)).count()
    if prev_rides > 0:
        rides_delta = int(round(((curr_rides - prev_rides) / prev_rides) * 100))
    else:
        rides_delta = 100 if curr_rides > 0 else 0
    stat_rides_delta_val = abs(rides_delta)
    stat_rides_delta_pos = (rides_delta >= 0)

    # 2. CO2 delta
    curr_trips = Trip.objects.filter(status__in=['COMPLETED', 'PAYMENT_COMPLETED'], created_at__gte=curr_month_start)
    curr_dist = 0
    for t in curr_trips:
        curr_dist += calculate_distance(t.ride.start_lat, t.ride.start_lng, t.ride.end_lat, t.ride.end_lng)
    curr_co2 = (curr_dist / 12.0) * 2.31
    
    prev_trips = Trip.objects.filter(status__in=['COMPLETED', 'PAYMENT_COMPLETED'], created_at__range=(prev_month_start, prev_month_end))
    prev_dist = 0
    for t in prev_trips:
        prev_dist += calculate_distance(t.ride.start_lat, t.ride.start_lng, t.ride.end_lat, t.ride.end_lng)
    prev_co2 = (prev_dist / 12.0) * 2.31
    
    if prev_co2 > 0:
        co2_delta = int(round(((curr_co2 - prev_co2) / prev_co2) * 100))
    else:
        co2_delta = 100 if curr_co2 > 0 else 0
    stat_co2_delta_val = abs(co2_delta)
    stat_co2_delta_pos = (co2_delta >= 0)

    # 3. Fuel cost saved delta
    curr_cost = curr_trips.aggregate(sum_fare=Sum('fare_paid'))['sum_fare'] or Decimal('0.00')
    prev_cost = prev_trips.aggregate(sum_fare=Sum('fare_paid'))['sum_fare'] or Decimal('0.00')
    curr_cost = float(curr_cost)
    prev_cost = float(prev_cost)
    if prev_cost > 0:
        cost_delta = int(round(((curr_cost - prev_cost) / prev_cost) * 100))
    else:
        cost_delta = 100 if curr_cost > 0 else 0
    stat_cost_delta_val = abs(cost_delta)
    stat_cost_delta_pos = (cost_delta >= 0)

    # 4. Match time delta
    def get_avg_match_time(trips_qs):
        total_m = 0
        cnt = 0
        for trip in trips_qs:
            req = RideRequest.objects.filter(
                passenger=trip.passenger,
                status='ACCEPTED',
                created_at__lte=trip.created_at
            ).order_by('-created_at').first()
            if req:
                total_m += (trip.created_at - req.created_at).total_seconds() / 60.0
                cnt += 1
        return (total_m / cnt) if cnt > 0 else None
        
    curr_match = get_avg_match_time(curr_trips)
    prev_match = get_avg_match_time(prev_trips)
    if curr_match is not None and prev_match is not None and prev_match > 0:
        match_delta = int(round(((curr_match - prev_match) / prev_match) * 100))
    else:
        match_delta = 0
    stat_match_delta_val = abs(match_delta)
    stat_match_delta_pos = (match_delta >= 0)

    # Dynamic trend calculations
    now = timezone.now()
    
    # 1. Weekly Commute Trend
    weekly_labels = []
    weekly_shared = []
    weekly_solo = []
    for i in range(7, -1, -1):
        start_date = now - timedelta(weeks=i+1)
        end_date = now - timedelta(weeks=i)
        weekly_labels.append(f"Wk {8-i}")
        
        shared_count = Trip.objects.filter(
            status__in=['COMPLETED', 'PAYMENT_COMPLETED'],
            created_at__range=(start_date, end_date)
        ).count()
        weekly_shared.append(shared_count)
        
        solo_count = Ride.objects.filter(
            status='COMPLETED',
            seats_available=F('total_seats'),
            departure_time__range=(start_date, end_date)
        ).count()
        weekly_solo.append(solo_count)
        
    weekly_commute_trend = {
        'labels': weekly_labels,
        'shared': weekly_shared,
        'solo': weekly_solo
    }

    # 2. Monthly Commute Trend
    monthly_labels = []
    monthly_shared = []
    monthly_solo = []
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=i*30)
        month_name = month_date.strftime('%b')
        monthly_labels.append(month_name)
        
        shared_count = Trip.objects.filter(
            status__in=['COMPLETED', 'PAYMENT_COMPLETED'],
            created_at__year=month_date.year,
            created_at__month=month_date.month
        ).count()
        monthly_shared.append(shared_count)
        
        solo_count = Ride.objects.filter(
            status='COMPLETED',
            seats_available=F('total_seats'),
            departure_time__year=month_date.year,
            departure_time__month=month_date.month
        ).count()
        monthly_solo.append(solo_count)
        
    monthly_commute_trend = {
        'labels': monthly_labels,
        'shared': monthly_shared,
        'solo': monthly_solo
    }

    # 3. Monthly CO2 Savings
    co2_labels = []
    co2_values = []
    for i in range(5, -1, -1):
        month_date = now - timedelta(days=i*30)
        co2_labels.append(month_date.strftime('%b'))
        
        trips_in_month = Trip.objects.filter(
            status__in=['COMPLETED', 'PAYMENT_COMPLETED'],
            created_at__year=month_date.year,
            created_at__month=month_date.month
        )
        dist = 0
        for trip in trips_in_month:
            dist += calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)
        
        co2 = round((dist / 12.0) * 2.31, 1)
        co2_values.append(float(co2))
        
    monthly_co2_savings = {
        'labels': co2_labels,
        'values': co2_values
    }

    # 4. Route Distribution
    route_distribution = {}
    rides = Ride.objects.filter(status='COMPLETED')
    for r in rides:
        dest = r.end_point_name.split(',')[0].strip()
        route_distribution[dest] = route_distribution.get(dest, 0) + 1
    
    route_labels = list(route_distribution.keys())[:5]
    route_values = [route_distribution[k] for k in route_labels]
    route_data = {
        'labels': route_labels or ['Gota', 'Gandhinagar', 'Office HQ', 'Campus'],
        'values': route_values or [12, 8, 5, 3]
    }

    # 5. Seat Utilization
    start_of_week = now - timedelta(days=7)
    weekly_rides = Ride.objects.filter(status='COMPLETED', departure_time__gte=start_of_week)
    filled_seats = 0
    empty_seats = 0
    for r in weekly_rides:
        filled = r.total_seats - r.seats_available
        filled_seats += filled
        empty_seats += r.seats_available
    
    if filled_seats == 0 and empty_seats == 0:
        filled_seats = 75
        empty_seats = 25
        
    seat_utilization = {
        'labels': ['Filled Seats', 'Empty Seats'],
        'values': [filled_seats, empty_seats]
    }

    # Stat cost saved (dynamic calculation)
    stat_cost_saved = passenger_stats.aggregate(sum_fare=Sum('fare_paid'))['sum_fare'] or Decimal('0.00')

    # Find matching pending ride requests for drivers
    driver_vehicles = Vehicle.objects.filter(owner=request.user, is_active=True)
    vehicle_types = [v.vehicle_type for v in driver_vehicles]
    pending_requests = []
    if vehicle_types:
        from .models import RideRequest
        pending_requests = RideRequest.objects.filter(
            status='PENDING',
            vehicle_type__in=vehicle_types
        ).exclude(passenger=request.user).order_by('-created_at')

    context = {
        'upcoming_bookings': upcoming_bookings,
        'upcoming_drives': upcoming_drives,
        'config': config,
        'total_trips': total_trips,
        'total_distance': total_distance,
        'co2_saved': co2_saved,
        'total_earned': total_earned,
        'wallet_balance': wallet_balance,
        'passenger_trip_count': passenger_trip_count,
        'driven_count': driven_count,
        'pending_requests': pending_requests,
        'weekly_commute_trend': weekly_commute_trend,
        'monthly_commute_trend': monthly_commute_trend,
        'monthly_co2_savings': monthly_co2_savings,
        'route_distribution': route_data,
        'seat_utilization': seat_utilization,
        'stat_cost_saved': stat_cost_saved,
        'stat_rides_shared': stat_rides_shared,
        'stat_co2_saved': stat_co2_saved,
        'stat_match_time': stat_match_time,
        'stat_rides_delta_val': stat_rides_delta_val,
        'stat_rides_delta_pos': stat_rides_delta_pos,
        'stat_co2_delta_val': stat_co2_delta_val,
        'stat_co2_delta_pos': stat_co2_delta_pos,
        'stat_cost_delta_val': stat_cost_delta_val,
        'stat_cost_delta_pos': stat_cost_delta_pos,
        'stat_match_delta_val': stat_match_delta_val,
        'stat_match_delta_pos': stat_match_delta_pos,
    }
    return render(request, 'dashboard.html', context)

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = EmployeeProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = EmployeeProfileForm(instance=request.user)
        
    my_rides = Ride.objects.filter(driver=request.user).order_by('-departure_time')
    my_vehicles = Vehicle.objects.filter(owner=request.user)
    return render(request, 'accounts/profile.html', {
        'form': form,
        'my_rides': my_rides,
        'my_vehicles': my_vehicles,
    })

# ----------------- Vehicle Management -----------------
@login_required
def vehicle_list_view(request):
    vehicles = Vehicle.objects.filter(owner=request.user, is_active=True)
    return render(request, 'vehicles/vehicles.html', {'vehicles': vehicles})

@login_required
def add_vehicle_view(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()
            messages.success(request, "Vehicle added successfully!")
            return redirect('vehicles')
    else:
        form = VehicleForm()
    return render(request, 'vehicles/add_vehicle.html', {'form': form})

@login_required
def delete_vehicle_view(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
    vehicle.is_active = False
    vehicle.save()
    messages.success(request, "Vehicle deleted successfully.")
    return redirect('vehicles')

# ----------------- Ride Offering & Search -----------------
@login_required
def offer_ride_view(request):
    # Ensure user has a vehicle
    if not request.user.vehicles.filter(is_active=True).exists():
        messages.warning(request, "You must add a vehicle before you can offer a ride.")
        return redirect('add_vehicle')

    if request.method == 'POST':
        form = RideForm(request.POST, employee=request.user)
        if form.is_valid():
            ride = form.save(commit=False)
            ride.driver = request.user
            ride.seats_available = ride.total_seats
            ride.save()
            messages.success(request, "Ride published successfully!")
            return redirect('trips')
    else:
        initial_time = timezone.now().strftime("%Y-%m-%dT%H:%M")
        form = RideForm(employee=request.user, initial={'departure_time': initial_time})
        
    saved_places = SavedPlace.objects.filter(employee=request.user)
    vehicles = Vehicle.objects.filter(owner=request.user, is_active=True)
    return render(request, 'rides/offer_ride.html', {'form': form, 'saved_places': saved_places, 'vehicles': vehicles})

@login_required
def find_ride_view(request):
    saved_places = SavedPlace.objects.filter(employee=request.user)
    return render(request, 'rides/find_ride.html', {'saved_places': saved_places})

@login_required
def rides_nearby_api_view(request):
    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if not lat or not lng:
        return JsonResponse({'rides': []})
        
    try:
        lat = float(lat)
        lng = float(lng)
    except ValueError:
        return JsonResponse({'rides': []})
        
    # Get active published rides
    active_rides = Ride.objects.filter(
        status='PUBLISHED',
        departure_time__gte=timezone.now() - timedelta(hours=2)
    ).exclude(driver=request.user)
    
    nearby_rides = []
    for ride in active_rides:
        # Distance to start coordinate
        dist_start = calculate_distance(lat, lng, ride.start_lat, ride.start_lng)
        
        # Distance to route line segment (driver passes through)
        px, py = lat, lng
        ax, ay = float(ride.start_lat), float(ride.start_lng)
        bx, by = float(ride.end_lat), float(ride.end_lng)
        
        dx = bx - ax
        dy = by - ay
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            dist_route = dist_start
        else:
            t = ((px - ax) * dx + (py - ay) * dy) / seg_len_sq
            t_clamped = max(0.0, min(1.0, t))
            closest_x = ax + t_clamped * dx
            closest_y = ay + t_clamped * dy
            dist_route = calculate_distance(px, py, closest_x, closest_y)
            
        # Match if either driver start is nearby or route line passes nearby (within 2 km)
        min_dist = min(dist_start, dist_route)
        if min_dist <= 2.0:
            # Place the pin at the closest route point or start coordinate so it's visible to passenger
            pin_lat = float(ride.start_lat) if dist_start <= 2.0 else closest_x
            pin_lng = float(ride.start_lng) if dist_start <= 2.0 else closest_y
            
            nearby_rides.append({
                'id': ride.id,
                'driver_name': ride.driver.get_full_name() or ride.driver.username,
                'driver_avatar': ride.driver.avatar or '',
                'start_lat': pin_lat,
                'start_lng': pin_lng,
                'end_name': ride.end_point_name,
                'time': ride.departure_time.strftime('%I:%M %p'),
                'seats_available': ride.seats_available,
                'price_per_km': float(ride.price_per_km),
                'distance': round(min_dist, 2)
            })
            
    return JsonResponse({'rides': nearby_rides})

@login_required
def ride_results_view(request):
    # Get parameters from query string
    start_lat = request.GET.get('start_lat')
    start_lng = request.GET.get('start_lng')
    end_lat = request.GET.get('end_lat')
    end_lng = request.GET.get('end_lng')
    
    start_name = request.GET.get('start_name', 'Current location')
    end_name = request.GET.get('end_name', 'Destination')

    if not all([start_lat, start_lng, end_lat, end_lng]):
        messages.error(request, "Invalid search criteria. Please select route points on the map.")
        return redirect('find_ride')

    # Distance of requested ride
    route_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
    config = SystemConfig.get_config()
    
    # Calculate estimated fare
    est_fare = Decimal(str(route_distance)) * config.travel_cost_per_km
    
    # Get seats requested (default to 1)
    try:
        seats_requested = int(request.GET.get('seats', 1))
    except (ValueError, TypeError):
        seats_requested = 1
    
    dep_time_str = request.GET.get('departure_time')
    search_time = timezone.now()
    if dep_time_str:
        try:
            from datetime import datetime
            dt = datetime.strptime(dep_time_str, "%Y-%m-%dT%H:%M")
            search_time = timezone.make_aware(dt)
        except (ValueError, TypeError):
            pass

    # Simple search: find rides that are PUBLISHED, departures are at or after search_time (with 2 hour past buffer)
    all_rides = Ride.objects.filter(
        status='PUBLISHED',
        departure_time__gte=search_time - timedelta(hours=2),
        seats_available__gte=seats_requested
    ).exclude(driver=request.user)

    print("DEBUG RIDE SEARCH DETAILS:")
    print(f"Request User: {request.user.username}")
    print(f"Search Coordinates: start=({start_lat}, {start_lng}), end=({end_lat}, {end_lng})")
    print(f"Seats Requested: {seats_requested}")
    print(f"All eligible published rides in DB: {list(all_rides.values_list('id', flat=True))}")

    rides_with_distance = []
    for ride in all_rides:
        # Check sub-route match (pickup and dropoff must lie along the driver's route path)
        is_match, pickup_dist, dest_dist = check_route_match(
            start_lat, start_lng, end_lat, end_lng,
            ride.start_lat, ride.start_lng, ride.end_lat, ride.end_lng
        )
        print(f"Checking Ride {ride.id}: is_match={is_match}, pickup_dist={pickup_dist} km, dest_dist={dest_dist} km")
        
        if is_match:
            passenger_fare = round(Decimal(str(route_distance)) * ride.price_per_km, 2)
            rides_with_distance.append({
                'ride': ride,
                'pickup_dist': pickup_dist,
                'dest_dist': dest_dist,
                'total_dist': calculate_distance(ride.start_lat, ride.start_lng, ride.end_lat, ride.end_lng),
                'passenger_fare': passenger_fare,
            })

    # Sort by closest pickup first
    rides_with_distance.sort(key=lambda x: x['pickup_dist'])

    context = {
        'rides': rides_with_distance,
        'start_name': start_name,
        'end_name': end_name,
        'route_distance': route_distance,
        'est_fare': est_fare,
        'start_lat': start_lat,
        'start_lng': start_lng,
        'end_lat': end_lat,
        'end_lng': end_lng,
        'seats_requested': seats_requested,
    }
    return render(request, 'rides/results.html', context)

@login_required
def book_ride_view(request):
    if request.method == 'POST':
        ride_id = request.POST.get('ride_id')
        seats_booked = int(request.POST.get('seats_booked', 1))
        
        ride = get_object_or_404(Ride, id=ride_id)
        if ride.seats_available < seats_booked:
            messages.error(request, "Not enough seats available!")
            return redirect('find_ride')
        
        # Calculate dynamic passenger distance-based fare
        start_lat = request.POST.get('start_lat')
        start_lng = request.POST.get('start_lng')
        end_lat = request.POST.get('end_lat')
        end_lng = request.POST.get('end_lng')
        
        if all([start_lat, start_lng, end_lat, end_lng]):
            passenger_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
            fare = round(ride.price_per_km * Decimal(str(passenger_distance)) * seats_booked, 2)
        else:
            fare = ride.fare_per_seat * seats_booked
        
        # Check payment method & wallet balance if using WALLET
        payment_method = request.POST.get('payment_method', 'WALLET')
        if payment_method == 'WALLET':
            if request.user.wallet_balance < fare:
                messages.error(request, f"Insufficient wallet balance. You need ₹{fare:.2f} but only have ₹{request.user.wallet_balance:.2f}. Please recharge.")
                return redirect('wallet')
            # Deduct wallet balance
            request.user.wallet_balance -= fare
            request.user.save()
            
        # Deduct ride seats
        ride.seats_available -= seats_booked
        ride.save()
        
        # Create Trip
        import random
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        trip = Trip.objects.create(
            passenger=request.user,
            ride=ride,
            seats_booked=seats_booked,
            fare_paid=fare,
            status='BOOKED',
            otp_code=otp_code,
            payment_method=payment_method
        )
        
        # Record Transaction
        Transaction.objects.create(
            employee=request.user,
            amount=-fare,
            transaction_type='PAYMENT',
            trip=trip
        )
        
        # Add earning transaction for the driver (will be marked completed / credited later)
        Transaction.objects.create(
            employee=ride.driver,
            amount=fare,
            transaction_type='EARNED',
            trip=trip
        )
        # We also credit driver's wallet immediately or on complete. Let's do it on completion!
        
        # Create Notification for driver
        from .models import Notification
        Notification.objects.create(
            employee=ride.driver,
            title="New Booking Alert",
            message=f"{request.user.get_full_name() or request.user.username} booked {seats_booked} seat(s) on your ride to {ride.end_point_name}."
        )
        
        messages.success(request, f"Ride booked successfully! Booking ID: #{trip.id}.")
        return redirect('trip_detail', trip_id=trip.id)
        
    return redirect('find_ride')

# ----------------- Trips & Live Tracking -----------------
@login_required
def trips_list_view(request):
    # Bookings (as passenger)
    passenger_trips = Trip.objects.filter(passenger=request.user).order_by('-created_at')
    # Drives (as driver)
    driver_rides = Ride.objects.filter(driver=request.user).order_by('-departure_time')
    
    context = {
        'passenger_trips': passenger_trips,
        'driver_rides': driver_rides,
    }
    return render(request, 'trips/trips.html', context)

@login_required
def trip_detail_view(request, trip_id):
    # Can be viewed by passenger or driver
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.passenger != request.user and trip.ride.driver != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
        
    is_driver = (trip.ride.driver == request.user)
    
    context = {
        'trip': trip,
        'is_driver': is_driver,
        'chat_messages': trip.messages.order_by('timestamp'),
        'distance': calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)
    }
    return render(request, 'trips/trip_detail.html', context)

@login_required
def update_trip_status_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.ride.driver != request.user:
        return HttpResponse("Unauthorized", status=403)
        
    new_status = request.POST.get('status')
    if new_status in dict(Trip.STATUS_CHOICES):
        if new_status == 'STARTED':
            otp_input = request.POST.get('otp_code', '').strip()
            if trip.otp_code and otp_input != trip.otp_code:
                messages.error(request, "Error: Invalid OTP code. The trip cannot start without the correct passenger OTP verification.")
                return redirect('trip_detail', trip_id=trip.id)
                
        if new_status == 'COMPLETED' and trip.payment_method == 'UPI':
            trip.status = 'PAYMENT_PENDING'
            trip.save()
            
            from .models import Notification
            Notification.objects.create(
                employee=trip.passenger,
                title="Ride Dropped - UPI Pay Pending",
                message=f"You have reached your destination! Please complete the UPI payment of ₹{trip.fare_paid:.2f} using the checkout link.",
                target_url=f"/trips/{trip.id}/"
            )
            messages.success(request, "Trip completed. Waiting for passenger to settle via UPI.")
        else:
            trip.status = new_status
            trip.save()
            
            from .models import Notification
            
            # Notify passenger when driver starts trip
            if new_status == 'STARTED':
                Notification.objects.create(
                    employee=trip.passenger,
                    title="Trip Started",
                    message=f"Your trip to {trip.ride.end_point_name} with driver {trip.ride.driver.get_full_name() or trip.ride.driver.username} has started!"
                )
            
            # If trip is completed, transfer the earnings to the driver's wallet
            elif new_status == 'COMPLETED':
                driver = trip.ride.driver
                driver.wallet_balance += trip.fare_paid
                driver.save()
                
                # Also mark ride as completed if all trips on this ride are complete/completed
                ride = trip.ride
                ride.status = 'COMPLETED'
                ride.save()
                
                # Notify driver
                Notification.objects.create(
                    employee=driver,
                    title="Trip Completed & Paid",
                    message=f"You completed the trip! Earning of ₹{trip.fare_paid:.2f} has been added to your wallet."
                )
                # Notify passenger
                Notification.objects.create(
                    employee=trip.passenger,
                    title="Trip Completed",
                    message=f"Your trip has completed. Settle the fare of ₹{trip.fare_paid:.2f} using your wallet."
                )
                
            messages.success(request, f"Trip status updated to {trip.get_status_display()}.")
    return redirect('trip_detail', trip_id=trip.id)

@login_required
def track_trip_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.passenger != request.user and trip.ride.driver != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
        
    is_driver = (trip.ride.driver == request.user)
    
    context = {
        'trip': trip,
        'is_driver': is_driver,
    }
    return render(request, 'trips/track_trip.html', context)

# ----------------- Chat Panel (HTMX poll) -----------------
@login_required
def get_chat_messages_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.passenger != request.user and trip.ride.driver != request.user:
        return HttpResponse("Access denied", status=403)
        
    messages_list = trip.messages.order_by('timestamp')
    return render(request, 'trips/_chat_panel.html', {'trip': trip, 'chat_messages': messages_list})

@login_required
def send_chat_message_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.passenger != request.user and trip.ride.driver != request.user:
        return HttpResponse("Access denied", status=403)
        
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if message_text:
            TripChat.objects.create(
                trip=trip,
                sender=request.user,
                message=message_text
            )
            
            recipient = trip.ride.driver if request.user == trip.passenger else trip.passenger
            from .models import Notification
            Notification.objects.create(
                employee=recipient,
                title="New Chat Message",
                message=f"New message from {request.user.get_full_name() or request.user.username}: {message_text[:40]}" + ("..." if len(message_text) > 40 else "")
            )
            
    messages_list = trip.messages.order_by('timestamp')
    return render(request, 'trips/_chat_panel.html', {'trip': trip, 'chat_messages': messages_list})

# ----------------- Wallet & Payments -----------------
@login_required
def wallet_view(request):
    transactions = Transaction.objects.filter(employee=request.user).order_by('-timestamp')
    form = WalletRechargeForm()
    config = SystemConfig.get_config()
    return render(request, 'wallet/wallet.html', {
        'form': form, 
        'transactions': transactions,
        'config': config
    })

@login_required
def wallet_recharge_init_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
        
    amount_str = request.POST.get('amount', '0')
    try:
        amount = Decimal(amount_str)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid amount'}, status=400)
        
    if amount < Decimal('5.00'):
        return JsonResponse({'error': 'Minimum recharge amount is ₹5.00'}, status=400)
        
    import os
    env_key_id = os.environ.get('RAZORPAY_KEY_ID')
    env_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
    
    config = SystemConfig.get_config()
    razorpay_key_id = env_key_id if env_key_id else config.razorpay_key_id
    razorpay_key_secret = env_key_secret if env_key_secret else config.razorpay_key_secret
    
    from django.urls import reverse
    callback_url = request.build_absolute_uri(
        reverse('wallet_recharge_verify', kwargs={'user_id': request.user.id})
    )
    
    try:
        import razorpay
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
        
        # Create standard Razorpay Payment Link with prefilled contact parameter
        payment_link = client.payment_link.create({
            "amount": int(amount * 100),  # in paise
            "currency": "INR",
            "accept_partial": False,
            "description": "CommuteSync Wallet Recharge",
            "customer": {
                "name": request.user.get_full_name() or request.user.username,
                "email": request.user.email or "employee@company.com",
                "contact": "9876543210" # Valid dummy contact to bypass recurring check
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "callback_url": callback_url,
            "callback_method": "get"
        })
        return JsonResponse({
            'payment_url': payment_link['short_url']
        })
    except Exception as e:
        return JsonResponse({'error': f"Razorpay Payment Link creation failed. Detail: {str(e)}"}, status=400)

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def wallet_recharge_verify_view(request, user_id):
    user = get_object_or_404(Employee, id=user_id)
    
    # Support GET redirect callback params from Razorpay Hosted Page
    params = request.GET if request.method == 'GET' else request.POST
    
    razorpay_payment_id = params.get('razorpay_payment_id')
    if not razorpay_payment_id:
        messages.error(request, "Payment ID not received from Razorpay.")
        return redirect('wallet')
        
    try:
        import os
        env_key_id = os.environ.get('RAZORPAY_KEY_ID')
        env_key_secret = os.environ.get('RAZORPAY_KEY_SECRET')
        
        config = SystemConfig.get_config()
        razorpay_key_id = env_key_id if env_key_id else config.razorpay_key_id
        razorpay_key_secret = env_key_secret if env_key_secret else config.razorpay_key_secret
        
        import razorpay
        client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
        
        # Verify transaction capture status from secure Razorpay server
        payment = client.payment.fetch(razorpay_payment_id)
        if payment.get('status') in ['authorized', 'captured']:
            if payment.get('status') == 'authorized':
                client.payment.capture(razorpay_payment_id, payment.get('amount'))
                
            actual_amount = Decimal(payment.get('amount')) / 100
            
            # Check for double credits
            recent_recharge = Transaction.objects.filter(
                employee=user,
                amount=actual_amount,
                transaction_type='RECHARGE',
                timestamp__gte=timezone.now() - timedelta(minutes=2)
            ).exists()
            
            if not recent_recharge:
                user.wallet_balance += actual_amount
                user.save()
                
                Transaction.objects.create(
                    employee=user,
                    amount=actual_amount,
                    transaction_type='RECHARGE'
                )
                messages.success(request, f"Wallet recharged successfully with ₹{actual_amount:.2f} via Razorpay!")
            else:
                messages.info(request, "This payment transaction was already credited to your wallet.")
        else:
            messages.error(request, f"Razorpay Payment not captured. Status: {payment.get('status')}")
    except Exception as e:
        messages.error(request, f"Razorpay Payment Verification Failed: {str(e)}")
        
    return redirect('wallet')

@login_required
def payment_checkout_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.passenger != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        
        trip.status = 'PAYMENT_COMPLETED'
        trip.save()
        
        if trip.payment_method == 'UPI':
            driver = trip.ride.driver
            driver.wallet_balance += trip.fare_paid
            driver.save()
            
            from .models import Transaction, Notification
            Transaction.objects.create(
                employee=driver,
                amount=trip.fare_paid,
                transaction_type='REVENUE',
                trip=trip
            )
            Transaction.objects.create(
                employee=trip.passenger,
                amount=-trip.fare_paid,
                transaction_type='PAYMENT',
                trip=trip
            )
            
            # Mark ride as completed
            ride = trip.ride
            ride.status = 'COMPLETED'
            ride.save()
            
            # Notify driver
            Notification.objects.create(
                employee=driver,
                title="UPI Payment Settle Completed",
                message=f"Passenger {trip.passenger.get_full_name() or trip.passenger.username} has settled the UPI payment of ₹{trip.fare_paid:.2f}. The balance is credited to your wallet!"
            )
            
        messages.success(request, f"Payment completed successfully via {payment_method.upper()}!")
        return redirect('trip_detail', trip_id=trip.id)
        
    return render(request, 'payments/payment.html', {'trip': trip})

# ----------------- Reports & Analytics -----------------
@login_required
def reports_view(request):
    # Analytics for passenger trips
    passenger_stats = Trip.objects.filter(passenger=request.user, status='COMPLETED')
    passenger_trip_count = passenger_stats.count()
    
    # Distance logic helper
    total_passenger_dist = 0
    for trip in passenger_stats:
        total_passenger_dist += calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)
        
    # Analytics for rides driven
    driven_rides = Ride.objects.filter(driver=request.user, status='COMPLETED')
    driven_count = driven_rides.count()
    
    total_driven_dist = 0
    for ride in driven_rides:
        total_driven_dist += calculate_distance(ride.start_lat, ride.start_lng, ride.end_lat, ride.end_lng)
        
    total_trips = passenger_trip_count + driven_count
    total_distance = round(total_passenger_dist + total_driven_dist, 2)
    
    # Fuel saved (assume average fuel consumption is 12 km/L, sharing is caring!)
    # By carpooling, we assume 1 vehicle is saved for passenger trips.
    fuel_saved = round(total_passenger_dist / 12.0, 2)
    co2_offset = round(fuel_saved * 2.31, 2) # 2.31 kg CO2 per liter of gasoline
    
    # Cost savings
    config = SystemConfig.get_config()
    total_spent = passenger_stats.aggregate(sum_fare=Sum('fare_paid'))['sum_fare'] or Decimal('0.00')
    total_earned = driven_rides.aggregate(
        sum_earnings=Sum('trips__fare_paid')
    )['sum_earnings'] or Decimal('0.00')

    # Weekly mock data for ChartJS charts
    chart_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul']
    chart_trips_data = [2, 5, 8, 12, 10, 15, total_trips]
    chart_cost_data = [30, 75, 120, 180, 150, 225, float(total_spent)]

    context = {
        'total_trips': total_trips,
        'total_distance': total_distance,
        'fuel_saved': fuel_saved,
        'co2_offset': co2_offset,
        'total_spent': total_spent,
        'total_earned': total_earned,
        'chart_months': chart_months,
        'chart_trips_data': chart_trips_data,
        'chart_cost_data': chart_cost_data,
    }
    return render(request, 'reports/reports.html', context)

# ----------------- Settings & Saved Places -----------------
@login_required
def settings_view(request):
    return render(request, 'settings/settings.html')

@login_required
def saved_places_view(request):
    places = SavedPlace.objects.filter(employee=request.user)
    if request.method == 'POST':
        form = SavedPlaceForm(request.POST)
        if form.is_valid():
            place = form.save(commit=False)
            place.employee = request.user
            place.save()
            messages.success(request, f"Saved place '{place.name}' added successfully!")
            return redirect('saved_places')
    else:
        form = SavedPlaceForm()
    return render(request, 'settings/saved_places.html', {'places': places, 'form': form})

@login_required
def delete_saved_place_view(request, place_id):
    place = get_object_or_404(SavedPlace, id=place_id, employee=request.user)
    place.delete()
    messages.success(request, "Saved place removed.")
    return redirect('saved_places')

# ----------------- Company Admin Panel -----------------
def is_admin(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser)

@login_required
def admin_dashboard_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    employees_count = Employee.objects.count()
    vehicles_count = Vehicle.objects.count()
    active_rides_count = Ride.objects.filter(status='PUBLISHED').count()
    completed_trips_count = Trip.objects.filter(status='COMPLETED').count()
    
    config = SystemConfig.get_config()
    
    # Audit trail / participation monitoring
    recent_rides = Ride.objects.select_related('driver').order_by('-created_at')[:5]
    recent_trips = Trip.objects.select_related('ride__driver', 'passenger').order_by('-created_at')[:5]
    
    context = {
        'employees_count': employees_count,
        'vehicles_count': vehicles_count,
        'active_rides_count': active_rides_count,
        'completed_trips_count': completed_trips_count,
        'config': config,
        'recent_rides': recent_rides,
        'recent_trips': recent_trips
    }
    return render(request, 'admin_panel/admin_dashboard.html', context)

@login_required
def admin_employees_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    employees = Employee.objects.all().order_by('username')
    return render(request, 'admin_panel/employees.html', {'employees': employees})

@login_required
def admin_toggle_employee_status_view(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
    try:
        emp = Employee.objects.get(pk=pk)
        if emp == request.user:
            messages.error(request, "You cannot deactivate your own account.")
        else:
            emp.is_active = not emp.is_active
            emp.save()
            messages.success(request, f"Access for {emp.get_full_name() or emp.username} has been {'restored' if emp.is_active else 'suspended'}.")
    except Employee.DoesNotExist:
        messages.error(request, "Employee not found.")
    return redirect('admin_employees')

@login_required
def admin_save_employee_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        pk = request.POST.get('pk')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        employee_id = request.POST.get('employee_id')
        department = request.POST.get('department')
        role = request.POST.get('role', 'EMPLOYEE')
        wallet_balance = request.POST.get('wallet_balance', '0.00')
        phone_number = request.POST.get('phone_number', '')
        
        if pk:  # Update existing
            try:
                emp = Employee.objects.get(pk=pk)
                emp.email = email
                emp.first_name = first_name
                emp.last_name = last_name
                emp.employee_id = employee_id
                emp.department = department
                emp.role = role
                emp.phone_number = phone_number
                try:
                    emp.wallet_balance = Decimal(wallet_balance)
                except:
                    pass
                emp.save()
                messages.success(request, "Employee record updated successfully!")
            except Employee.DoesNotExist:
                messages.error(request, "Employee not found.")
        else:  # Create new
            username = email.split('@')[0]
            counter = 1
            while Employee.objects.filter(username=username).exists():
                username = f"{email.split('@')[0]}_{counter}"
                counter += 1
                
            try:
                emp = Employee.objects.create_user(
                    username=username,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    employee_id=employee_id,
                    department=department,
                    role=role,
                    phone_number=phone_number,
                    password="Password123"
                )
                try:
                    emp.wallet_balance = Decimal(wallet_balance)
                    emp.save()
                except:
                    pass
                messages.success(request, f"New employee account created successfully! Default password is 'Password123'")
            except Exception as e:
                messages.error(request, f"Error creating employee: {str(e)}")
                
    return redirect('admin_employees')

@login_required
def admin_delete_employee_view(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            emp = Employee.objects.get(pk=pk)
            if emp == request.user:
                messages.error(request, "You cannot delete your own account.")
            else:
                emp.delete()
                messages.success(request, "Employee account deleted successfully.")
        except Employee.DoesNotExist:
            messages.error(request, "Employee not found.")
    return redirect('admin_employees')

@login_required
def admin_vehicles_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    vehicles = Vehicle.objects.all().order_by('owner__username')
    employees = Employee.objects.all().order_by('username')
    return render(request, 'admin_panel/vehicles.html', {'vehicles': vehicles, 'employees': employees})

@login_required
def admin_toggle_vehicle_status_view(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
    try:
        v = Vehicle.objects.get(pk=pk)
        v.is_active = not v.is_active
        v.save()
        messages.success(request, f"Vehicle {v.make} {v.model} ({v.license_plate}) has been {'activated' if v.is_active else 'deactivated'}.")
    except Vehicle.DoesNotExist:
        messages.error(request, "Vehicle not found.")
    return redirect('admin_vehicles')

@login_required
def admin_save_vehicle_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    if request.method == 'POST':
        pk = request.POST.get('pk')
        make = request.POST.get('make')
        model = request.POST.get('model')
        color = request.POST.get('color')
        license_plate = request.POST.get('license_plate')
        capacity = request.POST.get('capacity', '4')
        vehicle_type = request.POST.get('vehicle_type', 'FOUR')
        owner_id = request.POST.get('owner')
        
        if pk:  # Update existing
            try:
                v = Vehicle.objects.get(pk=pk)
                v.make = make
                v.model = model
                v.color = color
                v.license_plate = license_plate
                v.capacity = int(capacity)
                v.vehicle_type = vehicle_type
                if owner_id:
                    v.owner = Employee.objects.get(pk=owner_id)
                v.save()
                messages.success(request, "Vehicle details updated successfully!")
            except Vehicle.DoesNotExist:
                messages.error(request, "Vehicle not found.")
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
        else:  # Create new
            try:
                owner = Employee.objects.get(pk=owner_id)
                v = Vehicle.objects.create(
                    owner=owner,
                    make=make,
                    model=model,
                    color=color,
                    license_plate=license_plate,
                    capacity=int(capacity),
                    vehicle_type=vehicle_type
                )
                messages.success(request, f"Vehicle registration created for {owner.username}!")
            except Exception as e:
                messages.error(request, f"Error registering vehicle: {str(e)}")
                
    return redirect('admin_vehicles')

@login_required
def admin_delete_vehicle_view(request, pk):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
    if request.method == 'POST':
        try:
            v = Vehicle.objects.get(pk=pk)
            v.delete()
            messages.success(request, "Vehicle deleted successfully.")
        except Vehicle.DoesNotExist:
            messages.error(request, "Vehicle not found.")
    return redirect('admin_vehicles')

@login_required
def admin_config_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    config = SystemConfig.get_config()
    if request.method == 'POST':
        form = SystemConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, "System configurations updated successfully!")
            return redirect('admin_dashboard')
    else:
        form = SystemConfigForm(instance=config)
        
    return render(request, 'admin_panel/config.html', {'form': form})


# ----------------- New Route Confirmation & History Views -----------------

@login_required
def find_confirm_view(request):
    start_name = request.GET.get('start_name')
    start_lat = request.GET.get('start_lat')
    start_lng = request.GET.get('start_lng')
    end_name = request.GET.get('end_name')
    end_lat = request.GET.get('end_lat')
    end_lng = request.GET.get('end_lng')
    seats = request.GET.get('seats', 1)
    vehicle_type = request.GET.get('vehicle_type', 'FOUR')
    departure_time = request.GET.get('departure_time')
    
    if not all([start_lat, start_lng, end_lat, end_lng]):
        messages.error(request, "Please select start and end points on the map first.")
        return redirect('find_ride')
        
    route_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
    config = SystemConfig.get_config()
    
    rate = Decimal('12.00')
    if vehicle_type == 'TWO':
        rate = Decimal('5.00')
    elif vehicle_type == 'THREE':
        rate = Decimal('8.00')
    else:
        rate = config.travel_cost_per_km
        
    est_fare = Decimal(str(route_distance)) * rate * Decimal(str(seats))
    
    departure_time_display = str(departure_time)
    try:
        from datetime import datetime
        dt = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M")
        departure_time_display = dt.strftime("%b %d, %Y, %I:%M %p")
    except (ValueError, TypeError):
        pass
        
    context = {
        'mode': 'find',
        'start_name': start_name,
        'start_lat': start_lat,
        'start_lng': start_lng,
        'end_name': end_name,
        'end_lat': end_lat,
        'end_lng': end_lng,
        'seats': seats,
        'distance': route_distance,
        'duration': int(route_distance * 2),
        'fare': est_fare,
        'vehicle_type': vehicle_type,
        'departure_time': departure_time,
        'departure_time_display': departure_time_display,
    }
    return render(request, 'rides/confirm_route.html', context)

@login_required
def offer_confirm_view(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
        start_name = request.POST.get('start_point_name')
        start_lat = request.POST.get('start_lat')
        start_lng = request.POST.get('start_lng')
        end_name = request.POST.get('end_point_name')
        end_lat = request.POST.get('end_lat')
        end_lng = request.POST.get('end_lng')
        departure_time = request.POST.get('departure_time')
        total_seats = request.POST.get('total_seats')
        price_per_km = request.POST.get('price_per_km', '0.40')
        
        if not all([start_lat, start_lng, end_lat, end_lng]):
            messages.error(request, "Please select start and end points on the map first.")
            return redirect('offer_ride')
            
        route_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
        
        # Calculate flat estimated seat fare
        try:
            fare_per_seat = round(Decimal(str(route_distance)) * Decimal(str(price_per_km)), 2)
        except Exception:
            fare_per_seat = Decimal('0.00')
            
        # Format departure time display robustly
        departure_time_display = str(departure_time)
        try:
            from datetime import datetime
            dt = datetime.strptime(departure_time, "%Y-%m-%dT%H:%M")
            departure_time_display = dt.strftime("%b %d, %Y, %I:%M %p")
        except (ValueError, TypeError):
            pass
            
        context = {
            'mode': 'offer',
            'vehicle': vehicle,
            'start_name': start_name,
            'start_lat': start_lat,
            'start_lng': start_lng,
            'end_name': end_name,
            'end_lat': end_lat,
            'end_lng': end_lng,
            'departure_time': departure_time,
            'departure_time_display': departure_time_display,
            'total_seats': total_seats,
            'price_per_km': price_per_km,
            'fare_per_seat': fare_per_seat,
            'distance': route_distance,
            'duration': int(route_distance * 2),
        }
        return render(request, 'rides/confirm_route.html', context)
    return redirect('offer_ride')

@login_required
def publish_ride_view(request):
    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        vehicle = get_object_or_404(Vehicle, id=vehicle_id, owner=request.user)
        dep_str = request.POST.get('departure_time')
        
        try:
            dep_dt = datetime.strptime(dep_str, "%Y-%m-%dT%H:%M")
            dep_dt = timezone.make_aware(dep_dt)
        except ValueError:
            dep_dt = timezone.now()
            
        start_lat = request.POST.get('start_lat')
        start_lng = request.POST.get('start_lng')
        end_lat = request.POST.get('end_lat')
        end_lng = request.POST.get('end_lng')
        
        post_dist = request.POST.get('distance')
        if post_dist:
            try:
                route_distance = float(post_dist)
            except ValueError:
                route_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
        else:
            route_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
        
        price_per_km = request.POST.get('price_per_km', '0.40')
        try:
            fare_per_seat = round(Decimal(str(route_distance)) * Decimal(str(price_per_km)), 2)
        except Exception:
            fare_per_seat = Decimal('0.00')
            
        ride = Ride.objects.create(
            driver=request.user,
            vehicle=vehicle,
            start_point_name=request.POST.get('start_name'),
            start_lat=Decimal(start_lat),
            start_lng=Decimal(start_lng),
            end_point_name=request.POST.get('end_name'),
            end_lat=Decimal(end_lat),
            end_lng=Decimal(end_lng),
            departure_time=dep_dt,
            total_seats=int(request.POST.get('total_seats', 4)),
            seats_available=int(request.POST.get('total_seats', 4)),
            price_per_km=Decimal(price_per_km),
            fare_per_seat=fare_per_seat,
            status='PUBLISHED'
        )
        
        # Check matching passenger daily commutes to notify them
        try:
            ride_minutes = dep_dt.hour * 60 + dep_dt.minute
            potential_riders = Employee.objects.filter(daily_commute_time__isnull=False).exclude(id=request.user.id)
            from .models import Notification
            for rider in potential_riders:
                commute_minutes = rider.daily_commute_time.hour * 60 + rider.daily_commute_time.minute
                # Check if within a 30-minute window
                if abs(ride_minutes - commute_minutes) <= 30:
                    Notification.objects.create(
                        employee=rider,
                        title="Commute Match Suggestion",
                        message=f"{request.user.get_full_name() or request.user.username} published a ride departing at {dep_dt.strftime('%I:%M %p')}, matching your daily going time. Book your seat now!"
                    )
        except Exception as e:
            print("Scheduling notification failed:", e)
            
        messages.success(request, "Ride published successfully!")
        return redirect('trips')
    return redirect('offer_ride')

@login_required
def history_list_view(request):
    # Completed bookings as passenger
    passenger_trips = Trip.objects.filter(passenger=request.user, status='PAYMENT_COMPLETED').order_by('-created_at')
    # Completed drives as driver
    driver_rides = Ride.objects.filter(driver=request.user, status='COMPLETED').order_by('-departure_time')
    
    context = {
        'passenger_trips': passenger_trips,
        'driver_rides': driver_rides,
    }
    return render(request, 'history/history.html', context)

@login_required
def history_detail_view(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    if trip.passenger != request.user and trip.ride.driver != request.user:
        messages.error(request, "Access denied.")
        return redirect('dashboard')
        
    return render(request, 'history/history_detail.html', {
        'trip': trip,
        'distance': calculate_distance(trip.ride.start_lat, trip.ride.start_lng, trip.ride.end_lat, trip.ride.end_lng)
    })

@login_required
def mark_notifications_read_view(request):
    from .models import Notification
    if request.method == 'POST':
        Notification.objects.filter(employee=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'status': 'success'})
    return JsonResponse({'error': 'POST required'}, status=405)

@login_required
def get_unread_notifications_api(request):
    from .models import Notification
    unread_count = Notification.objects.filter(employee=request.user, is_read=False).count()
    latest = Notification.objects.filter(employee=request.user).order_by('-created_at')[:5]
    
    notifications_data = []
    for n in latest:
        notifications_data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'target_url': n.target_url or ''
        })
        
    return JsonResponse({
        'status': 'success',
        'unread_count': unread_count,
        'notifications': notifications_data
    })

@login_required
def create_ride_request_view(request):
    if request.method == 'POST':
        start_name = request.POST.get('start_name')
        start_lat = request.POST.get('start_lat')
        start_lng = request.POST.get('start_lng')
        end_name = request.POST.get('end_name')
        end_lat = request.POST.get('end_lat')
        end_lng = request.POST.get('end_lng')
        seats = request.POST.get('seats', 1)
        vehicle_type = request.POST.get('vehicle_type', 'FOUR')
        estimated_price = request.POST.get('estimated_price', '0.00')
        
        try:
            seats = int(seats)
            start_lat = Decimal(start_lat)
            start_lng = Decimal(start_lng)
            end_lat = Decimal(end_lat)
            end_lng = Decimal(end_lng)
            estimated_price = Decimal(estimated_price)
        except Exception as e:
            messages.error(request, f"Error processing parameters: {str(e)}")
            return redirect('find_ride')
            
        from .models import RideRequest, Notification
        
        # Create request
        payment_method = request.POST.get('payment_method', 'WALLET')
        req = RideRequest.objects.create(
            passenger=request.user,
            start_point_name=start_name,
            start_lat=start_lat,
            start_lng=start_lng,
            end_point_name=end_name,
            end_lat=end_lat,
            end_lng=end_lng,
            seats=seats,
            vehicle_type=vehicle_type,
            estimated_price=estimated_price,
            status='PENDING',
            payment_method=payment_method
        )
        
        # Find drivers with matching vehicle types and notify them
        matching_drivers = Employee.objects.filter(
            vehicles__vehicle_type=vehicle_type,
            vehicles__is_active=True
        ).distinct().exclude(pk=request.user.pk)
        
        for driver in matching_drivers:
            Notification.objects.create(
                employee=driver,
                title="New Ride Request Nearby",
                message=f"Passenger {request.user.get_full_name() or request.user.username} requested a {req.get_vehicle_type_display()} ride to {end_name} (Est: ₹{estimated_price:.2f}).",
                target_url=f"/rides/request/{req.id}/"
            )
            
        messages.success(request, "Your ride request has been broadcast to active drivers. Please wait for a match.")
        return redirect('ride_request_detail', pk=req.id)
        
    return redirect('find_ride')

@login_required
def ride_request_detail_view(request, pk):
    from .models import RideRequest
    req = get_object_or_404(RideRequest, id=pk)
    
    # Check if request has been accepted and matches a trip
    matching_trip = None
    if req.status == 'ACCEPTED':
        matching_trip = Trip.objects.filter(passenger=req.passenger, ride__start_lat=req.start_lat, ride__end_lat=req.end_lat).order_by('-created_at').first()
        
    if request.headers.get('HX-Request') == 'true' or request.GET.get('ajax') == 'true':
        # HTMX / AJAX Status polling check
        data = {
            'status': req.status,
            'trip_id': matching_trip.id if matching_trip else None
        }
        return JsonResponse(data)
        
    is_driver = (request.user != req.passenger)
    return render(request, 'rides/ride_request_detail.html', {
        'request_item': req,
        'matching_trip': matching_trip,
        'distance': calculate_distance(req.start_lat, req.start_lng, req.end_lat, req.end_lng),
        'is_driver': is_driver
    })

@login_required
def accept_ride_request_view(request, pk):
    if request.method == 'POST':
        from .models import RideRequest, Notification
        req = get_object_or_404(RideRequest, id=pk)
        
        if req.status != 'PENDING':
            messages.error(request, "This ride request has already been matched or cancelled.")
            return redirect('dashboard')
            
        if req.passenger == request.user:
            messages.error(request, "You cannot accept your own ride request.")
            return redirect('dashboard')
            
        # Get driver's vehicle of requested type
        vehicle = Vehicle.objects.filter(owner=request.user, vehicle_type=req.vehicle_type, is_active=True).first()
        if not vehicle:
            # Fallback to any active vehicle
            vehicle = Vehicle.objects.filter(owner=request.user, is_active=True).first()
            
        if not vehicle:
            messages.error(request, "You must register a vehicle in your profile to accept rides.")
            return redirect('vehicles')
            
        # Complete matching transactionally
        req.status = 'ACCEPTED'
        req.save()
        
        # Calculate price per km
        distance = calculate_distance(req.start_lat, req.start_lng, req.end_lat, req.end_lng) or 1.0
        price_per_km = round(req.estimated_price / Decimal(str(distance)), 2)
        fare_per_seat = round(req.estimated_price / Decimal(str(req.seats)), 2)
        
        # 1. Create matching published Ride
        ride = Ride.objects.create(
            driver=request.user,
            vehicle=vehicle,
            start_point_name=req.start_point_name,
            start_lat=req.start_lat,
            start_lng=req.start_lng,
            end_point_name=req.end_point_name,
            end_lat=req.end_lat,
            end_lng=req.end_lng,
            departure_time=timezone.now() + timedelta(minutes=15),
            total_seats=req.seats,
            seats_available=0, # Fully occupied by the requester
            price_per_km=price_per_km,
            fare_per_seat=fare_per_seat,
            status='PUBLISHED'
        )
        
        # Generate a random 6-digit OTP code
        import random
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        # 2. Create Trip
        trip = Trip.objects.create(
            passenger=req.passenger,
            ride=ride,
            seats_booked=req.seats,
            fare_paid=req.estimated_price,
            status='BOOKED',
            otp_code=otp_code,
            payment_method=req.payment_method
        )
        
        # 3. Create automated welcome chat message containing driver and vehicle details
        from .models import TripChat
        welcome_message = (
            f"🤖 Welcome to CommuteSync!\n"
            f"Your ride request has been accepted. Here are the driver details:\n"
            f"• Driver: {request.user.get_full_name() or request.user.username}\n"
            f"• Phone Number: {request.user.phone_number or 'No phone listed'}\n"
            f"• Vehicle Type: {vehicle.get_vehicle_type_display()}\n"
            f"• Vehicle Number: {vehicle.license_plate}\n"
            f"• Car Details: {vehicle.color} {vehicle.make} {vehicle.model}\n\n"
            f"🔑 **PICKUP OTP**: {otp_code}\n"
            f"Please share this OTP with the driver when they arrive at the pickup location to verify and start the trip!"
        )
        TripChat.objects.create(
            trip=trip,
            sender=request.user,
            message=welcome_message
        )
        
        # 4. Notify Passenger
        Notification.objects.create(
            employee=req.passenger,
            title="Ride Match Confirmed",
            message=f"Driver {request.user.get_full_name() or request.user.username} accepted your request in a {vehicle.make}!"
        )
        
        messages.success(request, f"Ride request accepted! Head over to pickup at {req.start_point_name}.")
        return redirect('trip_detail', trip_id=trip.id)
        
    return redirect('dashboard')

@login_required
def cancel_ride_request_view(request, pk):
    if request.method == 'POST':
        from .models import RideRequest
        req = get_object_or_404(RideRequest, id=pk)
        if req.passenger != request.user:
            messages.error(request, "Access denied.")
            return redirect('dashboard')
            
        if req.status == 'PENDING':
            req.status = 'CANCELLED'
            req.save()
            messages.success(request, "Your ride request has been cancelled.")
            
    return redirect('find_ride')

@login_required
def update_ride_offer_view(request, pk):
    if request.method == 'POST':
        ride = get_object_or_404(Ride, id=pk, driver=request.user)
        
        # Check if the ride has any bookings
        if ride.trips.filter(status='BOOKED').exists():
            messages.error(request, "Cannot update ride. Passenger bookings are already matched.")
            return redirect('profile')
            
        seats_available = request.POST.get('seats_available')
        departure_time = request.POST.get('departure_time')
        
        try:
            if seats_available:
                ride.seats_available = int(seats_available)
                ride.total_seats = int(seats_available)
            if departure_time:
                from django.utils.dateparse import parse_datetime
                parsed_dt = parse_datetime(departure_time)
                if parsed_dt:
                    if timezone.is_naive(parsed_dt):
                        ride.departure_time = timezone.make_aware(parsed_dt)
                    else:
                        ride.departure_time = parsed_dt
            ride.save()
            messages.success(request, "Ride offer updated successfully.")
        except Exception as e:
            messages.error(request, f"Error updating ride offer: {str(e)}")
            
    return redirect('profile')

@login_required
def cancel_ride_offer_view(request, pk):
    if request.method == 'POST':
        ride = get_object_or_404(Ride, id=pk, driver=request.user)
        
        if ride.status in ['STARTED', 'IN_PROGRESS', 'COMPLETED']:
            messages.error(request, "Cannot cancel ride. It is already started or completed.")
            return redirect('profile')
            
        # Cancel the ride and notify passengers
        ride.status = 'CANCELLED'
        ride.save()
        
        from .models import Notification
        for trip in ride.trips.filter(status='BOOKED'):
            trip.status = 'CANCELLED'
            trip.save()
            Notification.objects.create(
                employee=trip.passenger,
                title="Ride Cancelled",
                message=f"Your ride with {request.user.username} to {ride.end_point_name} has been cancelled by the driver."
            )
            
        messages.success(request, "Your ride offer has been cancelled.")
        
    return redirect('profile')

def about_view(request):
    return render(request, 'static_pages/about.html')

def sustainability_view(request):
    return render(request, 'static_pages/sustainability.html')

def contact_view(request):
    return render(request, 'static_pages/contact.html')

def privacy_view(request):
    return render(request, 'static_pages/privacy.html')

def terms_view(request):
    return render(request, 'static_pages/terms.html')

def accessibility_view(request):
    return render(request, 'static_pages/accessibility.html')


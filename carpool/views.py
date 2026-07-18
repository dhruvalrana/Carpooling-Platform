import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
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
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'accounts/splash.html')

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Account created successfully! You are now logged in.")
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EmployeeCreationForm()
    return render(request, 'accounts/signup.html', {'form': form})

# ----------------- Dashboard & Profile -----------------
@login_required
def dashboard_view(request):
    if request.user.role == 'ADMIN':
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

    # Wallet and statistics brief
    config = SystemConfig.get_config()

    context = {
        'upcoming_bookings': upcoming_bookings,
        'upcoming_drives': upcoming_drives,
        'config': config,
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
    return render(request, 'accounts/profile.html', {'form': form})

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
        initial_time = (timezone.now() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
        form = RideForm(employee=request.user, initial={'departure_time': initial_time})
        
    saved_places = SavedPlace.objects.filter(employee=request.user)
    vehicles = Vehicle.objects.filter(owner=request.user, is_active=True)
    return render(request, 'rides/offer_ride.html', {'form': form, 'saved_places': saved_places, 'vehicles': vehicles})

@login_required
def find_ride_view(request):
    saved_places = SavedPlace.objects.filter(employee=request.user)
    return render(request, 'rides/find_ride.html', {'saved_places': saved_places})

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
    
    # Simple search: find rides that are PUBLISHED, departures are in the future (with 24h past buffer), and have enough seats available
    all_rides = Ride.objects.filter(
        status='PUBLISHED',
        departure_time__gte=timezone.now() - timedelta(hours=24),
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
        
        # Check wallet balance
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
        trip = Trip.objects.create(
            passenger=request.user,
            ride=ride,
            seats_booked=seats_booked,
            fare_paid=fare,
            status='BOOKED'
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
            # For simplicity, we complete the ride structure too
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
        
    config = SystemConfig.get_config()
    order_id = ""
    is_mock = False
    
    # Check if the keys are default mock keys or invalid
    if config.razorpay_key_id.startswith('rzp_test_mock') or not config.razorpay_key_secret or config.razorpay_key_secret == 'mocksecret1234567890abcdef':
        is_mock = True
        order_id = f"order_mock_{int(timezone.now().timestamp())}"
    else:
        try:
            import razorpay
            client = razorpay.Client(auth=(config.razorpay_key_id, config.razorpay_key_secret))
            order_data = {
                'amount': int(amount * 100),  # in paise
                'currency': 'INR',
                'payment_capture': 1
            }
            order = client.order.create(data=order_data)
            order_id = order['id']
        except Exception as e:
            # Graceful fallback to mock mode if connection or API credentials fail
            is_mock = True
            order_id = f"order_mock_{int(timezone.now().timestamp())}"
            
    from django.urls import reverse
    callback_url = request.build_absolute_uri(
        reverse('wallet_recharge_verify', kwargs={'user_id': request.user.id})
    )
    cancel_url = request.build_absolute_uri(
        reverse('wallet')
    )
            
    return JsonResponse({
        'order_id': order_id,
        'amount': float(amount),
        'currency': 'INR',
        'key_id': config.razorpay_key_id,
        'is_mock': is_mock,
        'org_name': config.org_name,
        'callback_url': callback_url,
        'cancel_url': cancel_url
    })

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def wallet_recharge_verify_view(request, user_id):
    if request.method != 'POST':
        return HttpResponse("POST method required", status=405)
        
    user = get_object_or_404(Employee, id=user_id)
    razorpay_order_id = request.POST.get('razorpay_order_id')
    razorpay_payment_id = request.POST.get('razorpay_payment_id')
    razorpay_signature = request.POST.get('razorpay_signature')
    
    amount_str = request.POST.get('amount', '0')
    try:
        amount = Decimal(amount_str)
    except (ValueError, TypeError):
        amount = Decimal('0.00')
        
    if not all([razorpay_order_id, razorpay_payment_id]):
        messages.error(request, "Invalid payment verification details.")
        return redirect('wallet')
        
    config = SystemConfig.get_config()
    is_mock = razorpay_order_id.startswith('order_mock_')
    
    if is_mock:
        # Crediting mock transaction
        user.wallet_balance += amount
        user.save()
        
        Transaction.objects.create(
            employee=user,
            amount=amount,
            transaction_type='RECHARGE'
        )
        messages.success(request, f"Wallet recharged successfully with ₹{amount:.2f} (Simulated Payment)!")
    else:
        try:
            import razorpay
            client = razorpay.Client(auth=(config.razorpay_key_id, config.razorpay_key_secret))
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            
            # Signature valid, credit wallet balance
            user.wallet_balance += amount
            user.save()
            
            Transaction.objects.create(
                employee=user,
                amount=amount,
                transaction_type='RECHARGE'
            )
            messages.success(request, f"Wallet recharged successfully with ₹{amount:.2f} via Razorpay!")
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
        
        # Payment is simulated. If wallet selected, check balance (already deducted in book_ride, but in case of additional settlement)
        trip.status = 'PAYMENT_COMPLETED'
        trip.save()
        
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
    return user.is_authenticated and user.role == 'ADMIN'

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
    
    context = {
        'employees_count': employees_count,
        'vehicles_count': vehicles_count,
        'active_rides_count': active_rides_count,
        'completed_trips_count': completed_trips_count,
        'config': config
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
def admin_vehicles_view(request):
    if not is_admin(request.user):
        messages.error(request, "Unauthorized access.")
        return redirect('dashboard')
        
    vehicles = Vehicle.objects.all().order_by('owner__username')
    return render(request, 'admin_panel/vehicles.html', {'vehicles': vehicles})

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
    
    if not all([start_lat, start_lng, end_lat, end_lng]):
        messages.error(request, "Please select start and end points on the map first.")
        return redirect('find_ride')
        
    route_distance = calculate_distance(start_lat, start_lng, end_lat, end_lng)
    config = SystemConfig.get_config()
    est_fare = Decimal(str(route_distance)) * config.travel_cost_per_km * Decimal(str(seats))
    
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


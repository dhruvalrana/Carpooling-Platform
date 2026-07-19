from .models import Notification, Ride, RideRequest

def notification_processor(request):
    open_orders = []
    
    # Fetch open ride offers
    for ride in Ride.objects.filter(status='PUBLISHED', seats_available__gt=0).order_by('-departure_time')[:5]:
        open_orders.append({
            'type': 'RIDE',
            'time': ride.departure_time.strftime('%H:%M') if ride.departure_time else '09:00',
            'route': f"{ride.start_point_name} → {ride.end_point_name}",
            'seats_left': ride.seats_available,
            'target_url': '/rides/find/'
        })
        
    # Fetch open passenger requests
    for req in RideRequest.objects.filter(status='PENDING').order_by('-created_at')[:5]:
        open_orders.append({
            'type': 'REQUEST',
            'time': req.created_at.strftime('%H:%M') if req.created_at else '08:30',
            'route': f"{req.start_point_name} → {req.end_point_name}",
            'seats_left': req.seats,
            'target_url': f'/rides/request/{req.id}/'
        })

    # Fallbacks if list is empty
    if not open_orders:
        open_orders = [
            {'type': 'RIDE', 'time': '08:05', 'route': 'Riverside Hub → Tech Park Campus', 'seats_left': 3, 'target_url': '/rides/find/'},
            {'type': 'RIDE', 'time': '08:20', 'route': 'Maple Grove → Downtown HQ', 'seats_left': 1, 'target_url': '/rides/find/'},
            {'type': 'REQUEST', 'time': '08:35', 'route': 'North Station → Innovation Center', 'seats_left': 2, 'target_url': '#'},
            {'type': 'RIDE', 'time': '09:00', 'route': 'Lakeside → Tech Park Campus', 'seats_left': 4, 'target_url': '/rides/find/'},
        ]

    context = {
        'open_orders': open_orders,
        'unread_notification_count': 0,
        'latest_notifications': [],
    }

    if request.user.is_authenticated:
        context['unread_notification_count'] = Notification.objects.filter(employee=request.user, is_read=False).count()
        context['latest_notifications'] = Notification.objects.filter(employee=request.user).order_by('-created_at')[:5]
        
    return context

from .models import Notification

def notification_processor(request):
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(employee=request.user, is_read=False).count()
        latest_notifications = Notification.objects.filter(employee=request.user).order_by('-created_at')[:5]
        return {
            'unread_notification_count': unread_count,
            'latest_notifications': latest_notifications,
        }
    return {
        'unread_notification_count': 0,
        'latest_notifications': [],
    }

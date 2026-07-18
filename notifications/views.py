"""Notifications views."""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Notification


@login_required
def notifications_list(request):
    notifs = Notification.objects.filter(user=request.user)[:20]
    return render(request, 'notifications/list.html', {'notifications': notifs})


@login_required
@require_POST
def mark_read(request, pk):
    notif = Notification.objects.filter(pk=pk, user=request.user).first()
    if notif:
        notif.mark_read()
    return JsonResponse({'status': 'ok'})

"""Reports views."""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .services import personal_summary, org_summary


@login_required
def personal_reports(request):
    stats = personal_summary(request.user)
    return render(request, 'reports/personal.html', {'stats': stats})


@login_required
def org_reports(request):
    if not request.user.is_admin():
        messages.error(request, 'Admin access required.')
        return redirect('employee_dashboard')
    stats = org_summary(request.user.organization)
    return render(request, 'reports/org.html', {'stats': stats})


@login_required
def settings_hub(request):
    return render(request, 'reports/settings.html')

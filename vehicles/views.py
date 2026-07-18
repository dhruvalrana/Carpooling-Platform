"""Vehicle views — CRUD for employee's own vehicles."""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import Vehicle
from .forms import VehicleForm


@login_required
def my_vehicles(request):
    vehicles = Vehicle.objects.filter(owner=request.user, is_active=True)
    return render(request, 'vehicles/my_vehicles.html', {'vehicles': vehicles})


@login_required
def add_vehicle(request):
    form = VehicleForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        vehicle = form.save(commit=False)
        vehicle.owner = request.user
        vehicle.save()
        messages.success(request, 'Vehicle registered successfully.')
        return redirect('my_vehicles')
    return render(request, 'vehicles/vehicle_form.html', {'form': form, 'action': 'Add'})


@login_required
def edit_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    form = VehicleForm(data=request.POST or None, instance=vehicle)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Vehicle updated.')
        return redirect('my_vehicles')
    return render(request, 'vehicles/vehicle_form.html', {'form': form, 'action': 'Edit'})


@login_required
@require_POST
def delete_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, owner=request.user)
    vehicle.is_active = False
    vehicle.save()
    messages.success(request, 'Vehicle removed.')
    return redirect('my_vehicles')

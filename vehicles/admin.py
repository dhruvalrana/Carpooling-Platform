from django.contrib import admin
from .models import Vehicle

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('make', 'model', 'registration_number', 'owner', 'seating_capacity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('registration_number', 'make', 'model', 'owner__email')

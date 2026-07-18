from django.contrib import admin
from .models import Ride

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ('driver', 'pickup_label', 'destination_label', 'departure_datetime', 'seats_available', 'status')
    list_filter = ('status',)
    search_fields = ('driver__email', 'pickup_label', 'destination_label')

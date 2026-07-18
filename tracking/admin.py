from django.contrib import admin
from .models import LocationPing

@admin.register(LocationPing)
class LocationPingAdmin(admin.ModelAdmin):
    list_display = ('ride', 'lat', 'lng', 'recorded_at')

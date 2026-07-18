from rest_framework import serializers
from .models import Ride
from accounts.serializers import UserSerializer
from vehicles.serializers import VehicleSerializer


class RideSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.get_full_name', read_only=True)
    vehicle_display = serializers.SerializerMethodField()

    def get_vehicle_display(self, obj):
        return str(obj.vehicle) if obj.vehicle else ''

    class Meta:
        model = Ride
        fields = (
            'id', 'driver', 'driver_name', 'vehicle', 'vehicle_display',
            'pickup_label', 'pickup_lat', 'pickup_lng',
            'destination_label', 'destination_lat', 'destination_lng',
            'departure_datetime', 'seats_total', 'seats_available',
            'fare_per_seat', 'is_recurring', 'status', 'route_geometry', 'created_at',
        )
        read_only_fields = ('id', 'driver', 'seats_available', 'created_at')

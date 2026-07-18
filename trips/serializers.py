from rest_framework import serializers
from .models import Trip, Message


class TripSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='ride.driver.get_full_name', read_only=True)
    passenger_name = serializers.CharField(source='passenger.get_full_name', read_only=True)
    pickup_label = serializers.CharField(source='ride.pickup_label', read_only=True)
    destination_label = serializers.CharField(source='ride.destination_label', read_only=True)
    departure_datetime = serializers.DateTimeField(source='ride.departure_datetime', read_only=True)

    class Meta:
        model = Trip
        fields = (
            'id', 'ride', 'passenger', 'passenger_name', 'driver_name',
            'seats_booked', 'status', 'fare_amount',
            'pickup_label', 'destination_label', 'departure_datetime',
            'started_at', 'completed_at', 'created_at',
        )
        read_only_fields = ('id', 'passenger', 'status', 'fare_amount', 'started_at', 'completed_at', 'created_at')


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)

    class Meta:
        model = Message
        fields = ('id', 'trip', 'sender', 'sender_name', 'body', 'sent_at')
        read_only_fields = ('id', 'trip', 'sender', 'sent_at')

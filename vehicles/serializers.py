from rest_framework import serializers
from .models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)

    class Meta:
        model = Vehicle
        fields = ('id', 'make', 'model', 'registration_number', 'seating_capacity',
                  'color', 'is_active', 'owner', 'owner_name', 'created_at')
        read_only_fields = ('id', 'owner', 'created_at')

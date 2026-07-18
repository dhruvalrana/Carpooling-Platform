"""Accounts serializers."""
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'full_name', 'first_name', 'last_name',
                  'phone', 'photo', 'role', 'organization', 'is_active_on_platform')
        read_only_fields = ('id', 'email', 'role', 'organization')

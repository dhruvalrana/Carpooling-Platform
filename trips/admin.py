from django.contrib import admin
from .models import Trip, Message

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'passenger', 'ride', 'status', 'fare_amount', 'created_at')
    list_filter = ('status',)
    search_fields = ('passenger__email', 'ride__pickup_label')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('trip', 'sender', 'sent_at', 'body')
    list_filter = ('trip',)

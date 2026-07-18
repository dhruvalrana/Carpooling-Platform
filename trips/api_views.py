"""Trips API views."""
from rest_framework import generics, views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Trip, Message
from .serializers import TripSerializer, MessageSerializer
from .services import book_ride, transition
from core.exceptions import RideFullException, IllegalTripTransition


class TripListCreateView(generics.ListCreateAPIView):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Trip.objects.filter(passenger=self.request.user).select_related('ride', 'ride__driver')

    def create(self, request, *args, **kwargs):
        ride_id = request.data.get('ride')
        seats = int(request.data.get('seats_booked', 1))
        try:
            trip = book_ride(request.user, ride_id, seats)
            return Response(TripSerializer(trip).data, status=201)
        except (RideFullException, ValueError) as e:
            return Response({'error': str(e)}, status=400)


class MyTripsView(generics.ListAPIView):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Trip.objects.filter(passenger=self.request.user).select_related('ride')


class TripDetailView(generics.RetrieveAPIView):
    serializer_class = TripSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Trip.objects.filter(passenger=user) | Trip.objects.filter(ride__driver=user)


class TripStartView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, ride__driver=request.user)
        try:
            trip = transition(trip, Trip.STATUS_STARTED, actor=request.user)
            trip = transition(trip, Trip.STATUS_IN_PROGRESS, actor=request.user)
            return Response(TripSerializer(trip).data)
        except IllegalTripTransition as e:
            return Response({'error': str(e)}, status=400)


class TripCompleteView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        trip = get_object_or_404(Trip, pk=pk, ride__driver=request.user)
        try:
            trip = transition(trip, Trip.STATUS_COMPLETED, actor=request.user)
            trip = transition(trip, Trip.STATUS_PAYMENT_PENDING, actor=request.user)
            return Response(TripSerializer(trip).data)
        except IllegalTripTransition as e:
            return Response({'error': str(e)}, status=400)


class ChatMessagesView(generics.ListCreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_trip(self):
        user = self.request.user
        trip = get_object_or_404(Trip, pk=self.kwargs['trip_pk'])
        if trip.passenger != user and trip.ride.driver != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied
        return trip

    def get_queryset(self):
        return self.get_trip().messages.select_related('sender')

    def perform_create(self, serializer):
        trip = self.get_trip()
        serializer.save(trip=trip, sender=self.request.user)

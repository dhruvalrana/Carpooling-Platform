"""Rides API views."""
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Ride
from .serializers import RideSerializer
from .services import search_rides, get_route_preview, geocode


class RideListCreateView(generics.ListCreateAPIView):
    serializer_class = RideSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Ride.objects.filter(
            driver__organization=self.request.user.organization
        ).select_related('driver', 'vehicle')

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user)


class RideDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = RideSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Ride.objects.filter(driver__organization=self.request.user.organization)


class RideSearchView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pickup = request.query_params.get('pickup')
        destination = request.query_params.get('destination')
        date_str = request.query_params.get('date')
        time_str = request.query_params.get('time')
        seats = int(request.query_params.get('seats', 1))

        try:
            from datetime import date, time
            d = date.fromisoformat(date_str)
            t = time.fromisoformat(time_str)
            pickup_geo = geocode(pickup)
            dest_geo = geocode(destination)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

        rides = search_rides(
            org=request.user.organization,
            pickup_lat=pickup_geo['lat'],
            pickup_lng=pickup_geo['lng'],
            dest_lat=dest_geo['lat'],
            dest_lng=dest_geo['lng'],
            departure_date=d,
            departure_time=t,
            seats_needed=seats,
        )
        return Response(RideSerializer(rides, many=True).data)


class RoutePreviewView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        ride = generics.get_object_or_404(
            Ride.objects.filter(driver__organization=request.user.organization), pk=pk
        )
        route = get_route_preview(
            ride.pickup_lat, ride.pickup_lng,
            ride.destination_lat, ride.destination_lng,
        )
        return Response(route)

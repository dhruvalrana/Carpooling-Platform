from django import forms
from django.utils import timezone
from vehicles.models import Vehicle


class OfferRideForm(forms.Form):
    pickup_label = forms.CharField(
        label='Pickup Location',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter pickup address', 'id': 'id_pickup_label'}),
    )
    pickup_lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    pickup_lng = forms.FloatField(widget=forms.HiddenInput(), required=False)

    destination_label = forms.CharField(
        label='Destination',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter destination address', 'id': 'id_dest_label'}),
    )
    destination_lat = forms.FloatField(widget=forms.HiddenInput(), required=False)
    destination_lng = forms.FloatField(widget=forms.HiddenInput(), required=False)

    departure_datetime = forms.DateTimeField(
        label='Departure Date & Time',
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
    )
    seats_total = forms.IntegerField(
        label='Seats Available',
        min_value=1, max_value=8,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    fare_per_seat = forms.DecimalField(
        label='Fare per Seat (₹)',
        max_digits=10, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5'}),
    )
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.none(),
        label='Vehicle',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    is_recurring = forms.BooleanField(
        label='Repeat for next 5 weekdays',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].queryset = Vehicle.objects.filter(owner=user, is_active=True)

    def clean_departure_datetime(self):
        dt = self.cleaned_data['departure_datetime']
        if dt < timezone.now():
            raise forms.ValidationError('Departure time must be in the future.')
        return dt


class FindRideForm(forms.Form):
    pickup_label = forms.CharField(
        label='Pickup Location',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your pickup address'}),
    )
    destination_label = forms.CharField(
        label='Destination',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Where are you going?'}),
    )
    departure_date = forms.DateField(
        label='Date',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    departure_time = forms.TimeField(
        label='Time',
        widget=forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
    )
    seats_needed = forms.IntegerField(
        label='Seats',
        min_value=1, max_value=8,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )

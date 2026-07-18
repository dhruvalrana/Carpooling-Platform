from django import forms
from .models import Vehicle


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ('make', 'model', 'registration_number', 'seating_capacity', 'color')
        widgets = {
            'make': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Maruti'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Swift'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MH12AB1234'}),
            'seating_capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. White'}),
        }

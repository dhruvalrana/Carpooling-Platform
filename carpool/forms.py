from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Employee, Vehicle, Ride, SavedPlace, SystemConfig

class EmployeeCreationForm(UserCreationForm):
    employee_id = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'EMP12345'}))
    department = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Engineering'}))
    first_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John'}))
    last_name = forms.CharField(max_length=50, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Doe'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john.doe@company.com'}))
    role = forms.ChoiceField(choices=Employee.ROLE_CHOICES, initial='EMPLOYEE', widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta(UserCreationForm.Meta):
        model = Employee
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'employee_id', 'department', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-control'})

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'email', 'employee_id', 'department']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'employee_id': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
        }

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['make', 'model', 'license_plate', 'capacity', 'color', 'vehicle_type']
        widgets = {
            'make': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Toyota'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Prius'}),
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CA 12345'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 10}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Silver'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-select'}),
        }

class SavedPlaceForm(forms.ModelForm):
    class Meta:
        model = SavedPlace
        fields = ['name', 'address', 'latitude', 'longitude']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Home / Office'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '123 Main St'}),
            'latitude': forms.HiddenInput(attrs={'id': 'place_lat'}),
            'longitude': forms.HiddenInput(attrs={'id': 'place_lng'}),
        }

class RideForm(forms.ModelForm):
    departure_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
    )
    class Meta:
        model = Ride
        fields = [
            'vehicle', 'start_point_name', 'end_point_name', 
            'start_lat', 'start_lng', 'end_lat', 'end_lng', 
            'departure_time', 'total_seats', 'price_per_km'
        ]
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-select'}),
            'start_point_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search start point...'}),
            'end_point_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Search destination...'}),
            'start_lat': forms.HiddenInput(attrs={'id': 'start_lat'}),
            'start_lng': forms.HiddenInput(attrs={'id': 'start_lng'}),
            'end_lat': forms.HiddenInput(attrs={'id': 'end_lat'}),
            'end_lng': forms.HiddenInput(attrs={'id': 'end_lng'}),
            'total_seats': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 8}),
            'price_per_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'value': '0.40'}),
        }

    def __init__(self, *args, employee=None, **kwargs):
        super().__init__(*args, **kwargs)
        if employee:
            self.fields['vehicle'].queryset = Vehicle.objects.filter(owner=employee, is_active=True)

class WalletRechargeForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=8, decimal_places=2, min_value=5.00,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter amount (₹)', 'x-model': 'rechargeAmount'})
    )

class SystemConfigForm(forms.ModelForm):
    class Meta:
        model = SystemConfig
        fields = ['org_name', 'fuel_cost_per_km', 'travel_cost_per_km', 'razorpay_key_id', 'razorpay_key_secret']
        widgets = {
            'org_name': forms.TextInput(attrs={'class': 'form-control'}),
            'fuel_cost_per_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'travel_cost_per_km': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'razorpay_key_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'rzp_test_...'}),
            'razorpay_key_secret': forms.PasswordInput(render_value=True, attrs={'class': 'form-control'}),
        }

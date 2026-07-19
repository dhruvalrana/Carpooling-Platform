from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Employee, Vehicle, Ride, SavedPlace, SystemConfig

class EmployeeCreationForm(forms.ModelForm):
    name = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name'}))
    phone_number = forms.CharField(max_length=20, required=True, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email / Mobile'}))
    avatar = forms.CharField(required=False, widget=forms.HiddenInput(attrs={'id': 'id_avatar'}))
    
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}))

    class Meta:
        model = Employee
        fields = ('name', 'phone_number', 'email', 'avatar')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Employee.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data['email']
        user.email = email
        
        # Generate username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while Employee.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        user.username = username
        
        # Split name
        name_parts = self.cleaned_data['name'].strip().split(' ', 1)
        if len(name_parts) == 2:
            user.first_name = name_parts[0]
            user.last_name = name_parts[1]
        else:
            user.first_name = name_parts[0]
            user.last_name = ''
            
        user.phone_number = self.cleaned_data['phone_number']
        user.avatar = self.cleaned_data.get('avatar', '')
        
        # Set password
        user.set_password(self.cleaned_data["password1"])
        
        if commit:
            user.save()
        return user

class EmployeeProfileForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'email', 'daily_commute_time', 'avatar']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'daily_commute_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'avatar': forms.HiddenInput(attrs={'id': 'id_avatar'}),
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

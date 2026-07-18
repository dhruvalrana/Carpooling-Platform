"""Forms for accounts app."""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from organizations.models import Organization
from .models import User, SavedPlace




class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Work Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@company.com',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '••••••••',
        }),
    )


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        label='Work Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'you@company.com',
        }),
    )
    first_name = forms.CharField(
        label='First Name',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    last_name = forms.CharField(
        label='Last Name',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    phone = forms.CharField(
        label='Phone Number',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        domain = email.split('@')[-1]
        try:
            org = Organization.objects.get(domain=domain, is_active=True)
        except Organization.DoesNotExist:
            raise forms.ValidationError(
                f'No registered organization found for @{domain}. '
                'Ask your company admin to register the organization first.'
            )
        self._org = org
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.organization = self._org
        user.role = User.ROLE_EMPLOYEE
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'phone', 'photo', 'emergency_contact')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Name — Phone'}),
        }


class SavedPlaceForm(forms.ModelForm):
    class Meta:
        model = SavedPlace
        fields = ('label', 'address', 'lat', 'lng')
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Home, Office'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Start typing location...'}),
            'lat': forms.HiddenInput(),
            'lng': forms.HiddenInput(),
        }


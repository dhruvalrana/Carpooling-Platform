from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'organization', 'role', 'is_active_on_platform')
    list_filter = ('role', 'organization', 'is_active_on_platform')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    fieldsets = UserAdmin.fieldsets + (
        ('Organization & Role', {'fields': ('organization', 'role', 'phone', 'photo', 'emergency_contact', 'is_active_on_platform')}),
    )

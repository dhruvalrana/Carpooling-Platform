from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Employee, Vehicle, SavedPlace, Ride, Trip, TripChat, Transaction, SystemConfig

class EmployeeAdmin(UserAdmin):
    model = Employee
    list_display = ['username', 'email', 'employee_id', 'department', 'wallet_balance', 'role', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('employee_id', 'department', 'wallet_balance', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('employee_id', 'department', 'wallet_balance', 'role')}),
    )

admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Vehicle)
admin.site.register(SavedPlace)
admin.site.register(Ride)
admin.site.register(Trip)
admin.site.register(TripChat)
admin.site.register(Transaction)
admin.site.register(SystemConfig)

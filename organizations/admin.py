from django.contrib import admin
from .models import Organization, OrgSettings


class OrgSettingsInline(admin.StackedInline):
    model = OrgSettings
    can_delete = False
    extra = 1


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'domain')
    inlines = [OrgSettingsInline]


@admin.register(OrgSettings)
class OrgSettingsAdmin(admin.ModelAdmin):
    list_display = ('organization', 'currency', 'fuel_cost_per_km', 'max_search_radius_km')

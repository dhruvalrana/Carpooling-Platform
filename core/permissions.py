"""DRF permission classes for role-based access control."""
from rest_framework.permissions import BasePermission


class IsOrgAdmin(BasePermission):
    """Allows access only to users with role=ADMIN in their org."""
    message = 'Only organization admins can perform this action.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'role')
            and request.user.role == 'ADMIN'
        )


class IsEmployee(BasePermission):
    """Allows access to authenticated employees (includes admins)."""
    message = 'You must be an authenticated employee.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'organization')
            and request.user.organization is not None
        )


class IsOrgAdminOrReadOnly(BasePermission):
    """Write-access for admins; read-access for all authenticated org members."""
    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user and request.user.is_authenticated
        return (
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, 'role')
            and request.user.role == 'ADMIN'
        )

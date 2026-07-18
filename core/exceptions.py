"""Custom exceptions for the carpooling platform."""
from rest_framework.exceptions import APIException
from django.utils.translation import gettext_lazy as _


class RideFullException(Exception):
    """Raised when a ride has no available seats."""
    pass


class IllegalTripTransition(Exception):
    """Raised when an illegal trip status transition is attempted."""
    pass


class InsufficientWalletBalance(Exception):
    """Raised when a wallet doesn't have enough balance for a debit."""
    pass


class PaymentVerificationFailed(Exception):
    """Raised when Razorpay payment signature verification fails."""
    pass


class OrganizationAccessDenied(Exception):
    """Raised when a user tries to access data outside their org."""
    pass

"""
URL patterns for Guest Management
"""
from django.urls import path
from booking.guest_views import (
    AddGuestsToBookingView,
    GetBookingGuestsView,
    GuestCheckInView,
    GuestCheckOutView,
    AdminCheckInGuestView,
    AdminCheckOutGuestView,
)

urlpatterns = [
    # Guest management endpoints
    path('workspaces/<uuid:workspace_id>/bookings/<uuid:booking_id>/guests/', AddGuestsToBookingView.as_view(), name='add-guests'),
    path('workspaces/<uuid:workspace_id>/bookings/<uuid:booking_id>/guests/list/', GetBookingGuestsView.as_view(), name='get-booking-guests'),
    
    # Public guest check-in/out endpoints (no auth required)
    path('guests/check-in/', GuestCheckInView.as_view(), name='guest-check-in'),
    path('guests/check-out/', GuestCheckOutView.as_view(), name='guest-check-out'),
    
    # Admin guest management endpoints
    path('workspaces/<uuid:workspace_id>/guests/<uuid:guest_id>/check-in/', AdminCheckInGuestView.as_view(), name='admin-guest-check-in'),
    path('workspaces/<uuid:workspace_id>/guests/<uuid:guest_id>/check-out/', AdminCheckOutGuestView.as_view(), name='admin-guest-check-out'),
]

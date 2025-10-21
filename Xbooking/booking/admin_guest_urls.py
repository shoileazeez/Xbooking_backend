"""
URL routing for admin guest management endpoints (per booking)
"""
from django.urls import path
from booking.admin_guest_views import (
    AdminListPendingGuestsForBookingView,
    AdminVerifyGuestView,
    AdminRejectGuestView,
    AdminGuestDetailView,
    AdminGuestStatisticsView,
)

urlpatterns = [
    # List pending guests for a booking
    path(
        'workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/pending-guests/',
        AdminListPendingGuestsForBookingView.as_view(),
        name='admin-pending-guests-for-booking'
    ),
    
    # Verify a guest for a booking
    path(
        'workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/guests/<uuid:guest_id>/verify/',
        AdminVerifyGuestView.as_view(),
        name='admin-verify-guest'
    ),
    
    # Reject a guest for a booking
    path(
        'workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/guests/<uuid:guest_id>/reject/',
        AdminRejectGuestView.as_view(),
        name='admin-reject-guest'
    ),
    
    # Get guest details for a booking
    path(
        'workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/guests/<uuid:guest_id>/',
        AdminGuestDetailView.as_view(),
        name='admin-guest-detail'
    ),
    
    # Get guest statistics for a booking
    path(
        'workspaces/<uuid:workspace_id>/admin/bookings/<uuid:booking_id>/guests/stats/',
        AdminGuestStatisticsView.as_view(),
        name='admin-guest-statistics'
    ),
]

"""
URL routing for admin guest management endpoints (per booking)
"""
from django.urls import path
from booking.admin_guest_views import (
    AdminGuestDetailView,
    AdminGuestStatisticsView,
)

urlpatterns = [
    # Get guest details for a booking
    path(
        'guests/<uuid:guest_id>/',
        AdminGuestDetailView.as_view(),
        name='admin-guest-detail'
    ),
    
    # Get guest statistics for a booking
    path(
        'bookings/<uuid:booking_id>/guests/stats/',
        AdminGuestStatisticsView.as_view(),
        name='admin-guest-statistics'
    ),
]

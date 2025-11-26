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
    AdminQRCodeCheckInView,
    AdminQRCodeCheckOutView,
)
from booking.guest_qr_views import (
    GenerateGuestQRCodesView,
    ResendGuestQRCodeView,
)

urlpatterns = [
    # Guest management endpoints
    path('bookings/<uuid:booking_id>/guests/', AddGuestsToBookingView.as_view(), name='add-guests'),
    path('bookings/<uuid:booking_id>/guests/list/', GetBookingGuestsView.as_view(), name='get-booking-guests'),
    
    # Guest QR Code generation (after payment)
    path('bookings/<uuid:booking_id>/guests/generate-qr/', GenerateGuestQRCodesView.as_view(), name='generate-guest-qr'),
    path('guests/<uuid:guest_id>/resend-qr/', ResendGuestQRCodeView.as_view(), name='resend-guest-qr'),
    
    # Public guest check-in/out endpoints (no auth required)
    path('guests/check-in/', GuestCheckInView.as_view(), name='guest-check-in'),
    path('guests/check-out/', GuestCheckOutView.as_view(), name='guest-check-out'),
    
    # Admin guest management endpoints
    path('guests/<uuid:guest_id>/check-in/', AdminCheckInGuestView.as_view(), name='admin-guest-check-in'),
    path('guests/<uuid:guest_id>/check-out/', AdminCheckOutGuestView.as_view(), name='admin-guest-check-out'),
    
    # Admin QR code scan endpoints
    path('admin/guests/check-in/', AdminQRCodeCheckInView.as_view(), name='admin-qr-check-in'),
    path('admin/guests/check-out/', AdminQRCodeCheckOutView.as_view(), name='admin-qr-check-out'),
]

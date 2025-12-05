"""
QR Code and Notification URLs
"""
from django.urls import path
from qr_code.views import (
    GenerateOrderQRCodeView, GetOrderQRCodeView, GetBookingQRCodeView, FileUploadView
)
from qr_code.admin_views import (
    AdminCheckInView, AdminCheckOutView, AdminCheckInListView,
    AdminQRCodeDashboardView
)

app_name = 'qr_code'

urlpatterns = [
    # User QR Code URLs (Generate & Retrieve)
    path('orders/<uuid:order_id>/qr-code/generate/', 
         GenerateOrderQRCodeView.as_view(), name='generate_qr_code'),
    path('orders/<uuid:order_id>/qr-code/', 
         GetOrderQRCodeView.as_view(), name='get_qr_code'),
    
    # Booking QR Code URLs
    path('bookings/<uuid:booking_id>/qr-code/', 
         GetBookingQRCodeView.as_view(), name='get_booking_qr_code'),
    
    # File Upload URL (Unauthenticated - requires file_upload_key)
    path('upload/file/', 
         FileUploadView.as_view(), name='upload_file'),
    
    # Admin Check-In/Check-Out URLs (NEW)
    path('workspaces/<uuid:workspace_id>/admin/check-in/', 
         AdminCheckInView.as_view(), name='admin_check_in'),
    path('workspaces/<uuid:workspace_id>/admin/check-out/', 
         AdminCheckOutView.as_view(), name='admin_check_out'),
    path('workspaces/<uuid:workspace_id>/admin/check-ins/', 
         AdminCheckInListView.as_view(), name='admin_check_in_list'),
    path('workspaces/<uuid:workspace_id>/admin/check-in-dashboard/', 
         AdminQRCodeDashboardView.as_view(), name='admin_check_in_dashboard'),
]

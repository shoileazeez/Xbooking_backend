"""
QR Code and Notification URLs
"""
from django.urls import path
from qr_code.views import (
    GenerateOrderQRCodeView, GetOrderQRCodeView
)
from qr_code.admin_views import (
    AdminQRCodeDashboardView, AdminListPendingVerificationsView,
    AdminVerifyQRCodeView, AdminRejectQRCodeView, AdminQRCodeDetailsView,
    AdminVerificationStatsView, AdminResendQRCodeView
)

app_name = 'qr_code'

urlpatterns = [
    # User QR Code URLs (Generate & Retrieve)
    path('orders/<uuid:order_id>/qr-code/generate/', 
         GenerateOrderQRCodeView.as_view(), name='generate_qr_code'),
    path('orders/<uuid:order_id>/qr-code/', 
         GetOrderQRCodeView.as_view(), name='get_qr_code'),
    
    # Admin QR Code URLs (Verify & Manage)
    path('workspaces/<uuid:workspace_id>/admin/qr-code/dashboard/', 
         AdminQRCodeDashboardView.as_view(), name='admin_qr_dashboard'),
    path('workspaces/<uuid:workspace_id>/admin/qr-code/pending/', 
         AdminListPendingVerificationsView.as_view(), name='admin_pending_verifications'),
    path('workspaces/<uuid:workspace_id>/admin/qr-code/verify/', 
         AdminVerifyQRCodeView.as_view(), name='admin_verify_qr_code'),
    path('workspaces/<uuid:workspace_id>/admin/qr-code/reject/', 
         AdminRejectQRCodeView.as_view(), name='admin_reject_qr_code'),
    path('workspaces/<uuid:workspace_id>/admin/qr-code/<uuid:qr_code_id>/details/', 
         AdminQRCodeDetailsView.as_view(), name='admin_qr_code_details'),
    path('workspaces/<uuid:workspace_id>/admin/qr-code/stats/', 
         AdminVerificationStatsView.as_view(), name='admin_qr_stats'),
    path('workspaces/<uuid:workspace_id>/admin/qr-code/<uuid:qr_code_id>/resend/', 
         AdminResendQRCodeView.as_view(), name='admin_resend_qr_code'),
]

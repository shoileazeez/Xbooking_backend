"""
URLs for admin user management endpoints
"""
from django.urls import path
from workspace.views.admin_user_management import (
    AdminResetStaffPasswordView,
    AdminForcePasswordChangeView,
    AdminRevokeUserAccessView,
    AdminRestoreUserAccessView,
    AdminDeleteUserAccountView
)

urlpatterns = [
    # Password management
    path('users/<uuid:user_id>/reset-password/', 
         AdminResetStaffPasswordView.as_view(), 
         name='admin-reset-password'),
    
    path('users/<uuid:user_id>/force-password-change/', 
         AdminForcePasswordChangeView.as_view(), 
         name='admin-force-password-change'),
    
    # Access control
    path('users/<uuid:user_id>/revoke-access/', 
         AdminRevokeUserAccessView.as_view(), 
         name='admin-revoke-access'),
    
    path('users/<uuid:user_id>/restore-access/', 
         AdminRestoreUserAccessView.as_view(), 
         name='admin-restore-access'),
    
    # Account deletion
    path('users/<uuid:user_id>/delete-account/', 
         AdminDeleteUserAccountView.as_view(), 
         name='admin-delete-account'),
]

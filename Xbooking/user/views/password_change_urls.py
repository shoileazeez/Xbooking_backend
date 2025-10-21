"""
URLs for user password change endpoints
"""
from django.urls import path
from user.views.password_change import (
    ChangePasswordView,
    CheckPasswordChangeRequiredView,
    ForcedPasswordChangeView
)

urlpatterns = [
    # Check if password change required
    path('password-change-required/', 
         CheckPasswordChangeRequiredView.as_view(), 
         name='password-change-required'),
    
    # Normal password change (with current password verification)
    path('change-password/', 
         ChangePasswordView.as_view(), 
         name='change-password'),
    
    # Forced password change (after admin reset)
    path('forced-password-change/', 
         ForcedPasswordChangeView.as_view(), 
         name='forced-password-change'),
]

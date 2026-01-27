"""
User V1 URL Configuration
Production-ready routes with versioning
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from user.views.v1 import (
    UserRegistrationView,
    UserLoginView,
    RefreshTokenView,
    UserProfileView,
    UploadProfilePictureView,
    PasswordChangeView,
    ForcePasswordChangeView,
    OnboardingView,
    UserPreferenceViewSet,
)
from user.views.v1.password_reset import (
    PasswordResetRequestView,
    PasswordResetVerifyCodeView,
    PasswordResetConfirmView,
    ResendPasswordResetCodeView,
)

app_name = 'user_v1'

# Router for ViewSets
router = DefaultRouter()
router.register(r'preferences', UserPreferenceViewSet, basename='preference')

urlpatterns = [
    # Authentication
    path('auth/register/', UserRegistrationView.as_view(), name='register'),
    path('auth/login/', UserLoginView.as_view(), name='login'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),
    
    # Profile
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('profile/upload_picture/', UploadProfilePictureView.as_view(), name='upload-profile-picture'),
    
    # Password Management
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),
    path('password/force-change/', ForcePasswordChangeView.as_view(), name='force-password-change'),
    
    # Password Reset
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/verify/', PasswordResetVerifyCodeView.as_view(), name='password-reset-verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password-reset/resend/', ResendPasswordResetCodeView.as_view(), name='password-reset-resend'),
    
    # Onboarding
    path('onboarding/', OnboardingView.as_view(), name='onboarding'),
] + router.urls

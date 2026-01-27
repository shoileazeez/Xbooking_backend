"""
User V1 Views
Production-ready views with caching and EventBus
"""
from .auth import UserRegistrationView, UserLoginView, RefreshTokenView
from .profile import UserProfileView, UploadProfilePictureView
from .password import PasswordChangeView, ForcePasswordChangeView
from .onboarding import OnboardingView
from .preference import UserPreferenceViewSet

__all__ = [
    'UserRegistrationView',
    'UserLoginView',
    'RefreshTokenView',
    'UserProfileView',
    'UploadProfilePictureView',
    'PasswordChangeView',
    'ForcePasswordChangeView',
    'OnboardingView',
    'UserPreferenceViewSet',
]

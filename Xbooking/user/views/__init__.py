"""
User views package.
Use v1 views for all new code.
"""
from user.views.v1 import (
    UserRegistrationView,
    UserLoginView,
    RefreshTokenView,
    UserProfileView,
    PasswordChangeView,
    ForcePasswordChangeView,
    OnboardingView,
)

__all__ = [
    "UserRegistrationView",
    "UserLoginView",
    "RefreshTokenView",
    "UserProfileView",
    "PasswordChangeView",
    "ForcePasswordChangeView",
    "OnboardingView",
]

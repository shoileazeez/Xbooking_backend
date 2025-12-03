from django.urls import path
from user.views import (
    UserRegistrationView, 
    UserLoginView,
    ForgetPasswordView,
    PasswordResetConfirmView,
    ResendPasswordResetView,
    GoogleAuthView,
    RefreshTokenView
)


urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("auth/google/", GoogleAuthView.as_view(), name="google-auth"),
    path("token/refresh/", RefreshTokenView.as_view(), name="token-refresh"),
    path("forget-password/", ForgetPasswordView.as_view(), name="forget_password"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("resend-password-reset/", ResendPasswordResetView.as_view(), name="resend_password_reset"),
]
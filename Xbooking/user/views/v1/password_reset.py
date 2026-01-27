"""
Password Reset Views V1
Handles password reset request, OTP validation, and password confirmation
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.responses import SuccessResponse, ErrorResponse
from user.serializers.v1.password_reset import (
    PasswordResetRequestSerializer,
    PasswordResetVerifyCodeSerializer,
    PasswordResetConfirmSerializer,
    ResendPasswordResetCodeSerializer,
)


class PasswordResetRequestView(APIView):
    """
    Request password reset - sends OTP code to email
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(description='Reset code sent to email'),
            400: OpenApiResponse(description='Validation error'),
        },
        description='Request password reset and receive verification code via email',
        tags=['Authentication']
    )
    def post(self, request):
        """Request password reset"""
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid request',
                errors=serializer.errors,
                status_code=400
            )
        
        # Always return success for security (don't reveal if email exists)
        serializer.save()
        
        return SuccessResponse(
            message='If the email exists, a verification code has been sent to it.',
            data={'email': serializer.validated_data['email']}
        )


class PasswordResetVerifyCodeView(APIView):
    """
    Verify the reset code
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PasswordResetVerifyCodeSerializer,
        responses={
            200: OpenApiResponse(description='Code verified successfully'),
            400: OpenApiResponse(description='Invalid or expired code'),
        },
        description='Verify password reset code',
        tags=['Authentication']
    )
    def post(self, request):
        """Verify reset code"""
        serializer = PasswordResetVerifyCodeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid or expired code',
                errors=serializer.errors,
                status_code=400
            )
        
        return SuccessResponse(
            message='Code verified successfully. You can now reset your password.',
            data={'email': serializer.validated_data['email']}
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with new password
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(description='Password reset successfully'),
            400: OpenApiResponse(description='Validation error'),
        },
        description='Reset password with verification code and new password',
        tags=['Authentication']
    )
    def post(self, request):
        """Confirm password reset"""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Password reset failed',
                errors=serializer.errors,
                status_code=400
            )
        
        user = serializer.save()
        
        return SuccessResponse(
            message='Password reset successfully. You can now log in with your new password.',
            data={'email': user.email}
        )


class ResendPasswordResetCodeView(APIView):
    """
    Resend password reset code
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        request=ResendPasswordResetCodeSerializer,
        responses={
            200: OpenApiResponse(description='Code resent successfully'),
            400: OpenApiResponse(description='Validation error'),
        },
        description='Resend password reset verification code',
        tags=['Authentication']
    )
    def post(self, request):
        """Resend reset code"""
        serializer = ResendPasswordResetCodeSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ErrorResponse(
                message='Invalid request',
                errors=serializer.errors,
                status_code=400
            )
        
        # Always return success for security
        serializer.save()
        
        return SuccessResponse(
            message='If the email exists, a new verification code has been sent.',
            data={'email': serializer.validated_data['email']}
        )

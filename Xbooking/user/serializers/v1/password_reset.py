"""
Password Reset Serializers V1
Handles password reset request, OTP validation, and password confirmation
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Request password reset - generates and sends OTP code
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Check if user exists with this email"""
        try:
            user = User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            pass
        return value
    
    def save(self):
        """Generate reset code and send email"""
        from user.services.password_reset_service import PasswordResetService
        
        email = self.validated_data['email']
        try:
            user = User.objects.get(email=email, is_active=True)
            PasswordResetService.initiate_reset(user)
            return user
        except User.DoesNotExist:
            # Return None but don't raise error for security
            return None


class PasswordResetVerifyCodeSerializer(serializers.Serializer):
    """
    Verify the reset code
    """
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate(self, attrs):
        """Validate code and check expiration"""
        email = attrs.get('email')
        code = attrs.get('code')
        
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'Invalid email or code.'})
        
        # Check if code matches
        if user.password_reset_code != code:
            raise serializers.ValidationError({'code': 'Invalid verification code.'})
        
        # Check if code expired
        if user.password_reset_code_expires_at and user.password_reset_code_expires_at < timezone.now():
            raise serializers.ValidationError({'code': 'Verification code has expired. Please request a new one.'})
        
        attrs['user'] = user
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Confirm password reset with new password
    """
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        """Validate all fields"""
        email = attrs.get('email')
        code = attrs.get('code')
        new_password = attrs.get('new_password')
        confirm_password = attrs.get('confirm_password')
        
        # Check if user exists
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError({'email': 'Invalid email or code.'})
        
        # Check if code matches
        if user.password_reset_code != code:
            raise serializers.ValidationError({'code': 'Invalid verification code.'})
        
        # Check if code expired
        if user.password_reset_code_expires_at and user.password_reset_code_expires_at < timezone.now():
            raise serializers.ValidationError({'code': 'Verification code has expired. Please request a new one.'})
        
        # Check passwords match
        if new_password != confirm_password:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        
        # Validate password strength
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        attrs['user'] = user
        return attrs
    
    def save(self):
        """Update password and clear reset code"""
        user = self.validated_data['user']
        new_password = self.validated_data['new_password']
        
        # Set new password
        user.set_password(new_password)
        
        # Clear reset code
        user.password_reset_code = None
        user.password_reset_code_expires_at = None
        
        user.save()
        return user


class ResendPasswordResetCodeSerializer(serializers.Serializer):
    """
    Resend password reset code
    """
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Check if user exists"""
        try:
            user = User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Don't reveal if email exists for security
            pass
        return value
    
    def save(self):
        """Resend reset code"""
        from user.services.password_reset_service import PasswordResetService
        
        email = self.validated_data['email']
        try:
            user = User.objects.get(email=email, is_active=True)
            PasswordResetService.initiate_reset(user)
            return user
        except User.DoesNotExist:
            return None

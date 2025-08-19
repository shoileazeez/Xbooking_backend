from user.models import User, VerificationCode
from rest_framework import serializers
from user.utils.email_service import EmailService
from django.utils import timezone
from datetime import timedelta


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    verification_code = serializers.CharField(max_length=6, min_length=6, required=True)
    new_password = serializers.CharField(min_length=8, required=True)
    confirm_password = serializers.CharField(min_length=8, required=True)
    
    def validate_email(self, value):
        """
        Validate that the email exists in our system
        """
        try:
            user = User.objects.get(email=value.lower())
            if not user.is_active:
                raise serializers.ValidationError("This account has been deactivated.")
            return value.lower()
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
    
    def validate_verification_code(self, value):
        """
        Validate that the verification code is numeric and 6 digits
        """
        if not value.isdigit():
            raise serializers.ValidationError("Verification code must contain only numbers.")
        return value
    
    def validate_new_password(self, value):
        """
        Validate password strength using the same validation as registration
        """
        # Import password validation function
        from user.validators.registration import password_validation
        
        try:
            password_validation(value)
            return value
        except serializers.ValidationError as e:
            raise serializers.ValidationError(str(e))
    
    def validate(self, attrs):
        """
        Validate password match and verification code
        """
        # Check password match
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        
        # Get user and check verification code
        email = attrs['email']
        verification_code = attrs['verification_code']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email address.")
        
        # Check for valid verification code
        ten_minutes_ago = timezone.now() - timedelta(minutes=10)
        
        try:
            verification_record = VerificationCode.objects.get(
                user=user,
                code=verification_code,
                is_used=False,
                created_at__gte=ten_minutes_ago
            )
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError({
                'verification_code': 'Invalid or expired verification code. Please request a new one.'
            })
        
        # Store verification record and user for later use
        attrs['verification_record'] = verification_record
        attrs['user'] = user
        
        return attrs
    
    def save(self):
        """
        Reset user password and mark verification code as used
        """
        user = self.validated_data['user']
        verification_record = self.validated_data['verification_record']
        new_password = self.validated_data['new_password']
        
        # Update user password
        user.set_password(new_password)
        user.save()
        
        # Mark verification code as used
        verification_record.is_used = True
        verification_record.save()
        
        # Mark all other unused codes for this user as used (security measure)
        VerificationCode.objects.filter(
            user=user,
            is_used=False
        ).exclude(id=verification_record.id).update(is_used=True)
        
        # Send password change confirmation email
        EmailService.send_password_change_confirmation_email(user)
        
        return {
            'success': True,
            'message': 'Password reset successful',
            'data': {
                'email': user.email,
                'message': 'Your password has been updated successfully'
            }
        }

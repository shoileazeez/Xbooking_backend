from user.models import User, VerificationCode
from rest_framework import serializers
from user.utils.email_service import EmailService
from user.utils import check_existing_code
import random
import string
from django.utils import timezone
from datetime import timedelta


class ResendPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
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
    
    def validate(self, attrs):
        """
        Check if user already has a valid verification code that hasn't expired.
        For resend, we allow resending if the previous code is about to expire (less than 2 minutes remaining)
        """
        email = attrs.get('email')
        user = User.objects.get(email=email)
        
        # Check for existing unexpired verification codes
        existing_code_info = check_existing_code(user)
        
        if existing_code_info['exists']:
            remaining_time = existing_code_info['remaining_time']
            total_remaining_seconds = remaining_time['minutes'] * 60 + remaining_time['seconds']
            
            # Only allow resend if less than 2 minutes remaining or if explicitly requested
            if total_remaining_seconds > 120:  # More than 2 minutes remaining
                raise serializers.ValidationError(
                    f"A verification code was recently sent to this email. "
                    f"Please wait {remaining_time['minutes']} minutes and {remaining_time['seconds']} seconds "
                    f"before requesting a new code, or check your email for the existing code."
                )
        
        return attrs
    
    def generate_verification_code(self):
        """
        Generate a 6-digit verification code
        """
        return ''.join(random.choices(string.digits, k=6))
    
    def save(self):
        """
        Create new verification code and send email (resend functionality)
        """
        email = self.validated_data['email']
        user = User.objects.get(email=email)
        
        # Mark any existing unused codes as used
        VerificationCode.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True)
        
        # Generate new verification code
        verification_code = self.generate_verification_code()
        
        # Create verification code record
        verification_record = VerificationCode.objects.create(
            user=user,
            code=verification_code,
            is_used=False
        )
        
        # Send email using utility service
        email_sent = EmailService.send_password_reset_email(user, verification_code)
        
        if not email_sent:
            # If email fails, delete the verification code and raise error
            verification_record.delete()
            raise serializers.ValidationError(
                "Failed to resend verification email. Please try again later or contact support."
            )
        
        return {
            'success': True,
            'message': 'Verification code resent successfully',
            'data': {
                'email': user.email,
                'code_expires_in': '10 minutes',
                'resent_at': timezone.now().isoformat()
            }
        }

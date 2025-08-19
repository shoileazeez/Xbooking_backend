"""
Verification code utilities for XBooking user authentication system.
Handles generation, validation, and management of verification codes.
"""

import random
import string
from django.utils import timezone
from datetime import timedelta
from user.models import VerificationCode, User


class VerificationCodeService:
    """
    Service class for handling verification code operations.
    """
    
    CODE_EXPIRY_MINUTES = 10
    CODE_LENGTH = 6
    
    @staticmethod
    def generate_verification_code():
        """
        Generate a secure 6-digit verification code.
        
        Returns:
            str: 6-digit numeric verification code
        """
        return ''.join(random.choices(string.digits, k=VerificationCodeService.CODE_LENGTH))
    
    @staticmethod
    def check_existing_code(user):
        """
        Check if user has an existing valid verification code.
        
        Args:
            user: User instance
            
        Returns:
            dict: Contains 'exists' boolean and 'remaining_time' if exists
        """
        expiry_time = timezone.now() - timedelta(minutes=VerificationCodeService.CODE_EXPIRY_MINUTES)
        
        existing_code = VerificationCode.objects.filter(
            user=user,
            is_used=False,
            created_at__gte=expiry_time
        ).first()
        
        if existing_code:
            time_elapsed = timezone.now() - existing_code.created_at
            remaining_time = timedelta(minutes=VerificationCodeService.CODE_EXPIRY_MINUTES) - time_elapsed
            remaining_minutes = int(remaining_time.total_seconds() // 60)
            remaining_seconds = int(remaining_time.total_seconds() % 60)
            
            return {
                'exists': True,
                'remaining_time': {
                    'minutes': remaining_minutes,
                    'seconds': remaining_seconds,
                    'total_seconds': int(remaining_time.total_seconds())
                },
                'code_record': existing_code
            }
        
        return {'exists': False}
    
    @staticmethod
    def create_verification_code(user):
        """
        Create a new verification code for user.
        Marks any existing unused codes as used before creating new one.
        
        Args:
            user: User instance
            
        Returns:
            tuple: (verification_code_string, verification_record)
        """
        # Mark any existing unused codes as used
        VerificationCode.objects.filter(
            user=user,
            is_used=False
        ).update(is_used=True)
        
        # Generate new verification code
        verification_code = VerificationCodeService.generate_verification_code()
        
        # Create verification code record
        verification_record = VerificationCode.objects.create(
            user=user,
            code=verification_code,
            is_used=False
        )
        
        return verification_code, verification_record
    
    @staticmethod
    def validate_verification_code(user, code):
        """
        Validate a verification code for a user.
        
        Args:
            user: User instance
            code: Verification code string
            
        Returns:
            dict: Contains validation result and verification record if valid
        """
        if not code.isdigit() or len(code) != VerificationCodeService.CODE_LENGTH:
            return {
                'valid': False,
                'error': 'Verification code must be 6 digits.'
            }
        
        expiry_time = timezone.now() - timedelta(minutes=VerificationCodeService.CODE_EXPIRY_MINUTES)
        
        try:
            verification_record = VerificationCode.objects.get(
                user=user,
                code=code,
                is_used=False,
                created_at__gte=expiry_time
            )
            
            return {
                'valid': True,
                'verification_record': verification_record
            }
            
        except VerificationCode.DoesNotExist:
            return {
                'valid': False,
                'error': 'Invalid or expired verification code. Please request a new one.'
            }
    
    @staticmethod
    def mark_code_as_used(verification_record):
        """
        Mark a verification code as used and invalidate other codes for the same user.
        
        Args:
            verification_record: VerificationCode instance
        """
        # Mark the specific code as used
        verification_record.is_used = True
        verification_record.save()
        
        # Mark all other unused codes for this user as used (security measure)
        VerificationCode.objects.filter(
            user=verification_record.user,
            is_used=False
        ).exclude(id=verification_record.id).update(is_used=True)
    
    @staticmethod
    def cleanup_expired_codes():
        """
        Clean up expired verification codes from the database.
        This can be run as a periodic task.
        
        Returns:
            int: Number of codes cleaned up
        """
        expiry_time = timezone.now() - timedelta(minutes=VerificationCodeService.CODE_EXPIRY_MINUTES)
        
        # Count expired codes
        expired_count = VerificationCode.objects.filter(
            created_at__lt=expiry_time
        ).count()
        
        # Delete expired codes
        VerificationCode.objects.filter(
            created_at__lt=expiry_time
        ).delete()
        
        return expired_count
    
    @staticmethod
    def get_user_verification_history(user, limit=10):
        """
        Get verification code history for a user.
        
        Args:
            user: User instance
            limit: Maximum number of records to return
            
        Returns:
            QuerySet: Recent verification codes for the user
        """
        return VerificationCode.objects.filter(
            user=user
        ).order_by('-created_at')[:limit]


# Convenience functions
def generate_verification_code():
    """Convenience function for generating verification codes."""
    return VerificationCodeService.generate_verification_code()


def check_existing_code(user):
    """Convenience function for checking existing codes."""
    return VerificationCodeService.check_existing_code(user)


def create_verification_code(user):
    """Convenience function for creating verification codes."""
    return VerificationCodeService.create_verification_code(user)


def validate_verification_code(user, code):
    """Convenience function for validating verification codes."""
    return VerificationCodeService.validate_verification_code(user, code)


def mark_code_as_used(verification_record):
    """Convenience function for marking codes as used."""
    return VerificationCodeService.mark_code_as_used(verification_record)

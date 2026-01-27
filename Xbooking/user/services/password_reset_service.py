"""
Password Reset Service
Handles password reset logic including code generation and email sending
"""
import random
import string
from django.utils import timezone
from datetime import timedelta
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for handling password reset operations"""
    
    @staticmethod
    def generate_reset_code():
        """Generate 6-digit reset code"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def initiate_reset(user):
        """
        Initiate password reset process
        - Generate code
        - Set expiration
        - Send email
        """
        # Generate code
        code = PasswordResetService.generate_reset_code()
        
        # Set expiration (10 minutes from now)
        expiration = timezone.now() + timedelta(minutes=10)
        
        # Save to user
        user.password_reset_code = code
        user.password_reset_code_expires_at = expiration
        user.save(update_fields=['password_reset_code', 'password_reset_code_expires_at'])
        
        # Send email asynchronously
        send_password_reset_email_task.delay(user.id, code)
        
        logger.info(f"Password reset initiated for user {user.email}")
        
        return code


@shared_task
def send_password_reset_email_task(user_id, verification_code):
    """
    Celery task to send password reset email
    """
    from django.contrib.auth import get_user_model
    from user.utils.email_service import EmailService
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        EmailService.send_password_reset_email(user, verification_code)
        logger.info(f"Password reset email sent to {user.email}")
        return {'success': True, 'email': user.email}
    except User.DoesNotExist:
        logger.error(f"User with ID {user_id} not found")
        return {'success': False, 'error': 'User not found'}
    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}")
        return {'success': False, 'error': str(e)}

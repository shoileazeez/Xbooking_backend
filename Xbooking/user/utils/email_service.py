"""
Email utilities for XBooking user authentication system.
Handles sending various types of emails including password reset, verification, etc.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import logging

# Set up logging
logger = logging.getLogger(__name__)


class EmailService:
    """
    Service class for handling all email operations in the XBooking platform.
    """
    
    @staticmethod
    def get_default_context():
        """
        Get default context variables for all emails.
        """
        return {
            'platform_name': 'XBooking',
            'platform_url': 'https://xbooking.netlify.app/',
            'support_email': 'hello@xbooking.com',
            'help_center_url': 'https://xbooking.netlify.app/help',
            'privacy_policy_url': 'https://xbooking.netlify.app/privacy',
            'terms_of_service_url': 'https://xbooking.netlify.app/terms',
            'contact_url': 'https://xbooking.netlify.app/contact',
        }
    
    @staticmethod
    def send_password_reset_email(user, verification_code):
        """
        Send password reset email with verification code.
        
        Args:
            user: User instance
            verification_code: 6-digit verification code
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Prepare email context
            context = EmailService.get_default_context()
            context.update({
                'user_full_name': user.full_name,
                'verification_code': verification_code,
                'user_email': user.email,
            })
            
            # Render email templates
            html_message = render_to_string('emails/password_reset_email.html', context)
            plain_message = render_to_string('emails/password_reset_email.txt', context)
            
            # Email configuration
            subject = 'XBooking - Password Reset Verification Code'
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@xbooking.com')
            recipient_list = [user.email]
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent successfully to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_change_confirmation_email(user):
        """
        Send confirmation email after successful password change.
        
        Args:
            user: User instance
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Prepare email context
            context = EmailService.get_default_context()
            context.update({
                'user_full_name': user.full_name,
                'user_email': user.email,
            })
            
            # Render email templates
            html_message = render_to_string('emails/password_change_confirmation_email.html', context)
            plain_message = render_to_string('emails/password_change_confirmation_email.txt', context)
            
            # Email configuration
            subject = 'XBooking - Password Changed Successfully'
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@xbooking.com')
            recipient_list = [user.email]
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Password change confirmation email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password change confirmation email to {user.email}: {str(e)}")
            return False
    